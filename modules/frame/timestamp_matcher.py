import os
from typing import List, Dict, Any, Union

# --- Temporal Alignment Utilities ---

def _get_segment_attrs(seg: Union[dict, Any]) -> tuple[float, float, str, str]:
    """Helper to extract start, end, speaker, and text from dict or Pydantic SpeechSegment.

    Args:
        seg: Dictionary or Pydantic object representing a speech segment.

    Returns:
        tuple[float, float, str, str]: (start, end, speaker, text).
    """
    if isinstance(seg, dict):
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", 0.0))
        speaker = str(seg.get("speaker", "Unknown Speaker"))
        text = str(seg.get("text", "")).strip()
    else:
        start = float(getattr(seg, "start", 0.0))
        end = float(getattr(seg, "end", 0.0))
        speaker = str(getattr(seg, "speaker", "Unknown Speaker"))
        text = str(getattr(seg, "text", "")).strip()
    return start, end, speaker, text

# --- Primary Alignment Functions ---

def match_keyframes_with_dialogue(
    keyframes: List[Dict[str, Any]],
    speech_segments: List[Union[Dict[str, Any], Any]],
    default_speaker: str = "Unknown Speaker"
) -> List[Dict[str, Any]]:
    """Aligns video keyframes with timestamped STT dialogue segments.

    Computes active temporal boundaries for each keyframe panel and aggregates overlapping
    speech segments, determining dialogue text and primary speaker for panel typesetting.

    Args:
        keyframes: List of keyframe metadata dicts containing 'path', 'timestamp', 'frame_index'.
        speech_segments: List of speech segment dicts or Pydantic objects with 'start', 'end', 'speaker', 'text'.
        default_speaker: Fallback label when no speech overlaps a keyframe panel.

    Returns:
        List[Dict[str, Any]]: List of FrameDialoguePair dictionaries.
    """
    if not keyframes:
        return []

    sorted_keyframes = sorted(keyframes, key=lambda k: k.get("timestamp", 0.0))
    num_frames = len(sorted_keyframes)
    
    frame_dialogue_pairs = []

    # Step 1: Precompute panel active time windows
    panel_windows = []
    for idx, kf in enumerate(sorted_keyframes):
        curr_t = float(kf.get("timestamp", 0.0))
        if idx == 0:
            next_t = float(sorted_keyframes[1].get("timestamp", 0.0)) if num_frames > 1 else curr_t + 5.0
            t_start = max(0.0, curr_t - (next_t - curr_t) / 2.0)
        else:
            prev_t = float(sorted_keyframes[idx - 1].get("timestamp", 0.0))
            t_start = (prev_t + curr_t) / 2.0

        if idx == num_frames - 1:
            prev_t = float(sorted_keyframes[idx - 1].get("timestamp", 0.0)) if num_frames > 1 else curr_t - 2.5
            t_end = curr_t + (curr_t - prev_t) / 2.0
        else:
            next_t = float(sorted_keyframes[idx + 1].get("timestamp", 0.0))
            t_end = (curr_t + next_t) / 2.0

        panel_windows.append((t_start, t_end, kf))

    # Step 2: Assign each speech segment exclusively to the single panel with maximum temporal overlap
    panel_assigned_segments: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(num_frames)}

    if speech_segments:
        for seg in speech_segments:
            s_start, s_end, s_speaker, s_text = _get_segment_attrs(seg)
            if not s_text:
                continue

            best_panel_idx = -1
            max_overlap = 0.0

            for p_idx, (t_start, t_end, _) in enumerate(panel_windows):
                overlap_start = max(t_start, s_start)
                overlap_end = min(t_end, s_end)
                overlap_dur = max(0.0, overlap_end - overlap_start)
                if overlap_dur > max_overlap:
                    max_overlap = overlap_dur
                    best_panel_idx = p_idx

            # Fallback: if segment fell in a gap between panels, assign to closest panel by midpoint
            if best_panel_idx == -1:
                s_mid = (s_start + s_end) / 2.0
                best_panel_idx = min(range(num_frames), key=lambda i: abs(panel_windows[i][2].get("timestamp", 0.0) - s_mid))

            panel_assigned_segments[best_panel_idx].append({
                "start": s_start,
                "end": s_end,
                "speaker": s_speaker,
                "text": s_text,
                "overlap": round(max_overlap, 2)
            })

    # Step 3: Construct FrameDialoguePair objects
    for idx, (t_start, t_end, kf) in enumerate(panel_windows):
        curr_t = float(kf.get("timestamp", 0.0))
        segs = panel_assigned_segments[idx]

        speaker_overlaps: Dict[str, float] = {}
        merged_texts = []
        dialogue_by_speaker: List[Dict[str, str]] = []

        for seg in segs:
            s_speaker = seg["speaker"]
            s_text = seg["text"]
            s_overlap = seg["overlap"]
            merged_texts.append(s_text)
            speaker_overlaps[s_speaker] = speaker_overlaps.get(s_speaker, 0.0) + (s_overlap if s_overlap > 0 else 1.0)

            if dialogue_by_speaker and dialogue_by_speaker[-1]["speaker"] == s_speaker:
                dialogue_by_speaker[-1]["text"] = (dialogue_by_speaker[-1]["text"] + " " + s_text).strip()
            else:
                dialogue_by_speaker.append({"speaker": s_speaker, "text": s_text.strip()})

        if speaker_overlaps:
            primary_speaker = max(speaker_overlaps, key=speaker_overlaps.get)
        else:
            primary_speaker = default_speaker

        merged_dialogue = " ".join(merged_texts).strip()

        frame_dialogue_pairs.append({
            "keyframe_path": kf.get("path"),
            "timestamp": curr_t,
            "frame_index": kf.get("frame_index", 0),
            "panel_time_range": (round(t_start, 2), round(t_end, 2)),
            "speaker": primary_speaker,
            "dialogue": merged_dialogue,
            "dialogue_by_speaker": dialogue_by_speaker,
            "matching_segments": segs,
            "sharpness_score": kf.get("sharpness_score", 0.0),
            "trigger": kf.get("trigger", "unknown")
        })

    return frame_dialogue_pairs

def find_best_keyframe_for_segment(
    segment: Union[Dict[str, Any], Any],
    keyframes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Finds the single keyframe whose timestamp is closest to a speech segment midpoint.

    Args:
        segment: Speech segment dict or Pydantic object.
        keyframes: List of keyframe metadata dictionaries.

    Returns:
        Dict[str, Any]: Matching keyframe metadata dict or empty dict if keyframes is empty.
    """
    if not keyframes:
        return {}

    s_start, s_end, _, _ = _get_segment_attrs(segment)
    midpoint = (s_start + s_end) / 2.0

    best_kf = min(keyframes, key=lambda k: abs(float(k.get("timestamp", 0.0)) - midpoint))
    return best_kf
