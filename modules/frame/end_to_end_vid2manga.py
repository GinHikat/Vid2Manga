import os
import sys

# Ensure project root and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.config import settings
from modules.speech.process_audio import split_video_audio, speech2text
from modules.frame.human_detector import PersonSegmenter
from modules.frame.bubble_processor import Bubble, find_optimal_bubble_center
from modules.frame.manga_processor import (
    stylize_c,
    cv2_to_pil,
    generate_manga_layout,
    create_manga_page,
    save_manga_pages_to_pdf
)

def generate_video_manga_page(
    video: str,
    num_frames: int = 7,
    output_page_name: str = "final_manga_page.png",
    page_width: int = 1000,
    page_height: int = 1400,
    time_range: tuple = None,
    precomputed_speech_segments: list = None
) -> str:
    """Generates a single multi-panel manga page from a video file or video path.

    Args:
        video (str): Path to input video file or video object path.
        num_frames (int): Number of panels/frames to extract for this page (default: 7).
        output_page_name (str): Filename for final manga page PNG output.
        page_width (int): Target width for manga page canvas (default: 1000).
        page_height (int): Target height for manga page canvas (default: 1400).
        time_range (tuple, optional): (t_start, t_end) in seconds to constrain page scope.
        precomputed_speech_segments (list, optional): Precomputed STT speech segments to avoid re-execution.

    Returns:
        str: Absolute path to the generated manga page PNG.
    """
    video_path = str(video)
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    video_duration = total_frames / fps

    if time_range:
        range_start_sec, range_end_sec = time_range
        start_frame_idx = max(0, int(range_start_sec * fps))
        end_frame_idx = min(total_frames - 1, int(range_end_sec * fps))
    else:
        range_start_sec, range_end_sec = 0.0, video_duration
        start_frame_idx, end_frame_idx = 0, total_frames - 1

    section_duration = range_end_sec - range_start_sec
    section_total_frames = max(1, end_frame_idx - start_frame_idx)

    print("=" * 60)
    print(f"[START] Processing Manga Page (t = {range_start_sec:.1f}s to {range_end_sec:.1f}s) for: {video_path}")
    print("=" * 60)

    # --- Person-Validated Frame Scanning & Keyframe Selection ---
    print(f"\nScanning video section for {num_frames} distinct person-containing frames...")
    segmenter = PersonSegmenter()
    
    # Fast sampling: Sample candidate frames every 6.5 seconds in-memory
    sample_step = max(1, int(fps * 6.5))
    valid_person_frames = []

    for cand_idx in range(start_frame_idx, end_frame_idx, sample_step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, cand_idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        h_orig, w_orig = frame.shape[:2]
        scale = 720 / float(h_orig)
        frame_hd = cv2.resize(frame, (int(w_orig * scale), 720), interpolation=cv2.INTER_CUBIC)

        _, _, test_masks, _ = segmenter.segment(frame_hd)

        if len(test_masks) > 0:
            timestamp_sec = round(cand_idx / fps, 2)
            valid_person_frames.append({
                "frame_idx": cand_idx,
                "timestamp": timestamp_sec,
                "image": frame,
                "detected_masks": test_masks
            })

    print(f" -> Discovered {len(valid_person_frames)} frames containing detected person instances in section.")

    extracted_frames = []
    if len(valid_person_frames) >= num_frames:
        step_idx = len(valid_person_frames) / float(num_frames)
        for i in range(num_frames):
            chosen = valid_person_frames[min(int(i * step_idx), len(valid_person_frames) - 1)]
            chosen["index"] = i
            extracted_frames.append(chosen)
            print(f" -> Panel {i + 1}/{num_frames}: Selected Frame #{chosen['frame_idx']} (t = {chosen['timestamp']}s, Persons = {len(chosen['detected_masks'])})")
    else:
        for i in range(num_frames):
            if i < len(valid_person_frames):
                chosen = valid_person_frames[i]
            else:
                fallback_idx = start_frame_idx + min(i * (section_total_frames // num_frames), section_total_frames - 1)
                cap.set(cv2.CAP_PROP_POS_FRAMES, fallback_idx)
                _, frame = cap.read()
                chosen = {
                    "frame_idx": fallback_idx,
                    "timestamp": round(fallback_idx / fps, 2),
                    "image": frame,
                    "detected_masks": []
                }
            chosen["index"] = i
            extracted_frames.append(chosen)
            print(f" -> Panel {i + 1}/{num_frames}: Frame #{chosen['frame_idx']} (t = {chosen['timestamp']}s)")

    cap.release()

    if not extracted_frames:
        raise RuntimeError("No frames could be extracted from video section.")

    # --- Audio Extraction, Speech-to-Text & Speaker Diarization ---
    if precomputed_speech_segments is not None:
        print(f"\nReusing precomputed audio STT and speaker diarization segments ({len(precomputed_speech_segments)} segments)...")
        speech_segments = precomputed_speech_segments
    else:
        print(f"\nExtracting audio, transcribing dialogue and running speaker diarization...")
        audio_path, _ = split_video_audio(video_path)
        stt_result = speech2text(audio_path)
        speech_segments = stt_result.get("segments", [])
        print(f" -> Speech processing complete. Total STT segments: {len(speech_segments)}.")

    window_duration = section_duration / float(num_frames)
    for frame_data in extracted_frames:
        t_start = frame_data["timestamp"]
        t_end = t_start + window_duration
        
        frame_turns = []
        for seg in speech_segments:
            s_start = seg.get("start", 0.0)
            s_end = seg.get("end", 0.0)
            if max(s_start, t_start) < min(s_end, t_end):
                frame_turns.append({
                    "speaker": seg.get("speaker", "Unknown Speaker"),
                    "text": seg.get("text", "").strip()
                })
        
        frame_data["turns"] = frame_turns

    manga_frames = generate_manga_layout(
        width=page_width,
        height=page_height,
        num_frames=num_frames,
        seed=42,
        std_dev=0.05,
        margin=8
    )

    # --- Panel Stylization & Dialogue Typesetting ---
    print(f"\nProcessing {len(extracted_frames)} panels (Stylization & Speech Bubble Typesetting)...")
    bubble_tool = Bubble()
    processed_panel_images = []

    for i, frame_data in enumerate(extracted_frames):
        print(f" -> Processing Panel {i + 1}/{num_frames} (t = {frame_data['timestamp']}s)...")
        box_x, box_y, box_w, box_h = manga_frames[i]
        target_ar = float(box_w) / float(box_h)

        frame_img = frame_data["image"]
        h_orig, w_orig = frame_img.shape[:2]

        orig_ar = float(w_orig) / float(h_orig)
        if orig_ar > target_ar:
            new_w = int(h_orig * target_ar)
            crop_x = (w_orig - new_w) // 2
            frame_img = frame_img[:, crop_x : crop_x + new_w]
        elif orig_ar < target_ar:
            new_h = int(w_orig / target_ar)
            crop_y = (h_orig - new_h) // 2
            frame_img = frame_img[crop_y : crop_y + new_h, :]

        h_crop, w_crop = frame_img.shape[:2]
        target_h = 720
        scale = target_h / float(h_crop)
        target_w = int(w_crop * scale)
        frame_hd = cv2.resize(frame_img, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
        h, w = target_h, target_w

        stylized_cv2 = stylize_c(frame_hd)
        if stylized_cv2 is None:
            stylized_cv2 = frame_hd

        _, _, detected_masks, _ = segmenter.segment(frame_hd)

        person_masks = []
        if len(detected_masks) >= 2:
            person_masks = sorted(detected_masks, key=lambda m: np.sum(m), reverse=True)[:2]
        elif len(detected_masks) == 1:
            person_masks.append(detected_masks[0])
            m2 = np.zeros((h, w), dtype=np.uint8)
            cv2.ellipse(m2, (int(w * 0.75), int(h * 0.5)), (int(w * 0.15), int(h * 0.3)), 0, 0, 360, 1, -1)
            person_masks.append(m2)
        else:
            m1 = np.zeros((h, w), dtype=np.uint8)
            m2 = np.zeros((h, w), dtype=np.uint8)
            cv2.ellipse(m1, (int(w * 0.25), int(h * 0.5)), (int(w * 0.15), int(h * 0.35)), 0, 0, 360, 1, -1)
            cv2.ellipse(m2, (int(w * 0.75), int(h * 0.5)), (int(w * 0.15), int(h * 0.35)), 0, 0, 360, 1, -1)
            person_masks = [m1, m2]

        def get_cx(m):
            mom = cv2.moments(m)
            return int(mom["m10"] / mom["m00"]) if mom["m00"] > 0 else 0
        person_masks = sorted(person_masks[:2], key=get_cx)

        person_centroids = []
        safety_kernels = []
        for m in person_masks:
            mom = cv2.moments(m)
            cx = int(mom["m10"] / mom["m00"]) if mom["m00"] > 0 else w // 2
            cy = int(mom["m01"] / mom["m00"]) if mom["m00"] > 0 else h // 2
            person_centroids.append((cx, cy))
            
            kernel = np.ones((9, 9), np.uint8)
            dilated = cv2.dilate((m > 0).astype(np.uint8), kernel)
            safety_kernels.append(dilated)

        canvas = stylized_cv2.copy()

        raw_turns = frame_data["turns"]
        if not raw_turns:
            panel_pil = cv2_to_pil(canvas)
            processed_panel_images.append(panel_pil)
            continue

        turns = []
        for t in raw_turns:
            if turns and turns[-1]["speaker"] == t["speaker"]:
                turns[-1]["text"] += " " + t["text"]
            else:
                turns.append({"speaker": t["speaker"], "text": t["text"]})
        
        turns = turns[:2]

        total_person_mask = np.zeros((h, w), dtype=np.uint8)
        for m in detected_masks:
            total_person_mask[m > 0] = 255

        speaker_colors = [(0, 180, 255), (220, 0, 220), (0, 160, 0)]
        placed_bubble_boxes = []

        dilated_persons_tmp = cv2.dilate((total_person_mask > 0).astype(np.uint8), np.ones((25, 25), np.uint8))
        clear_space_tmp = (dilated_persons_tmp == 0).astype(np.uint8) * 255
        dist_map_tmp = cv2.distanceTransform(clear_space_tmp, cv2.DIST_L2, 5)
        max_open_space = np.max(dist_map_tmp[:int(h * 0.6), :])

        if max_open_space < 100:
            target_font_size = 16
            max_words_cap = 11
            max_line_chars = 10
            min_bw, min_bh = 150, 65
            line_spacing = 22
        else:
            target_font_size = 22
            max_words_cap = 18
            max_line_chars = 14
            min_bw, min_bh = 220, 90
            line_spacing = 30

        for k, turn in enumerate(turns):
            dialogue_text = turn["text"]
            speaker_label = turn["speaker"]
            spk_idx = 0 if "1" in speaker_label or k % 2 == 0 else 1
            color = speaker_colors[spk_idx % len(speaker_colors)]

            cx, cy = person_centroids[spk_idx]
            mask = person_masks[spk_idx]

            words = dialogue_text.split()
            if len(words) > max_words_cap:
                words = words[:max_words_cap]
                dialogue_text = " ".join(words) + "..."

            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", target_font_size)
                header_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", target_font_size)
            except Exception:
                font = ImageFont.load_default()
                header_font = ImageFont.load_default()

            header_text = f"[{speaker_label}]"

            lines = []
            cur_line = []
            for word in words:
                cur_line.append(word)
                if len(" ".join(cur_line)) > max_line_chars:
                    lines.append(" ".join(cur_line))
                    cur_line = []
            if cur_line:
                lines.append(" ".join(cur_line))

            temp_img = Image.new('RGB', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            h_bbox = temp_draw.textbbox((0, 0), header_text, font=header_font)
            header_w = h_bbox[2] - h_bbox[0]
            header_h = h_bbox[3] - h_bbox[1]

            max_line_w = header_w
            for line in lines:
                l_bbox = temp_draw.textbbox((0, 0), line, font=font)
                max_line_w = max(max_line_w, l_bbox[2] - l_bbox[0])

            total_text_h = header_h + len(lines) * line_spacing + 10
            bubble_w = max(min_bw, int(max_line_w * 1.45))
            bubble_h = max(min_bh, int(total_text_h * 1.50))

            pref_side = "left" if spk_idx == 0 else "right"
            y_target_min = 80 if k == 0 else 200
            
            bubble_cx, bubble_cy = find_optimal_bubble_center(
                total_person_mask=total_person_mask,
                bubble_w=bubble_w,
                bubble_h=bubble_h,
                preferred_side=pref_side,
                y_min=y_target_min,
                y_max=520
            )

            box_half_w = bubble_w // 2
            box_half_h = bubble_h // 2
            cur_box = [bubble_cx - box_half_w, bubble_cy - box_half_h, bubble_cx + box_half_w, bubble_cy + box_half_h]

            for prev_box in placed_bubble_boxes:
                if not (cur_box[2] < prev_box[0] - 15 or cur_box[0] > prev_box[2] + 15 or
                        cur_box[3] < prev_box[1] - 15 or cur_box[1] > prev_box[3] + 15):
                    bubble_cy = prev_box[3] + box_half_h + 15
                    cur_box = [bubble_cx - box_half_w, bubble_cy - box_half_h, bubble_cx + box_half_w, bubble_cy + box_half_h]

            margin_x = bubble_w // 2 + 50
            margin_y = bubble_h // 2 + 35
            bubble_cx = max(margin_x, min(w - margin_x, bubble_cx))
            bubble_cy = max(margin_y, min(h - margin_y, bubble_cy))

            body_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.ellipse(body_mask, (bubble_cx, bubble_cy), (bubble_w // 2, bubble_h // 2), 0, 0, 360, 255, -1)

            shift_dir = -15 if pref_side == "left" else 15
            shift_count = 0
            while np.sum((body_mask > 0) & (total_person_mask > 0)) > 0 and shift_count < 15:
                next_cx = bubble_cx + shift_dir
                if margin_x <= next_cx <= w - margin_x:
                    bubble_cx = next_cx
                else:
                    break
                body_mask = np.zeros((h, w), dtype=np.uint8)
                cv2.ellipse(body_mask, (bubble_cx, bubble_cy), (bubble_w // 2, bubble_h // 2), 0, 0, 360, 255, -1)
                shift_count += 1

            cur_box = [bubble_cx - box_half_w, bubble_cy - box_half_h, bubble_cx + box_half_w, bubble_cy + box_half_h]
            placed_bubble_boxes.append(cur_box)

            tail_mask = np.zeros((h, w), dtype=np.uint8)
            tail_pts = np.array([
                [bubble_cx - 10, bubble_cy + bubble_h // 2 - 3],
                [bubble_cx + 10, bubble_cy + bubble_h // 2 - 3],
                [bubble_cx + (-20 if spk_idx == 0 else 20), bubble_cy + bubble_h // 2 + 25]
            ], dtype=np.int32)
            cv2.fillPoly(tail_mask, [tail_pts], 255)

            target_angle = bubble_tool.calculate_relative_angle(body_mask, mask)
            if target_angle is None:
                target_angle = 135.0 if spk_idx == 0 else 45.0

            aligned_bubble_mask = bubble_tool.reattach_tail(body_mask, tail_mask, target_angle)

            bubble_contours, _ = cv2.findContours(aligned_bubble_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(canvas, bubble_contours, -1, (255, 255, 255), -1)
            cv2.drawContours(canvas, bubble_contours, -1, color, 3)

            bubble_kernel = np.ones((25, 25), np.uint8)
            dilated_bubble = cv2.dilate(aligned_bubble_mask, bubble_kernel)
            total_person_mask[dilated_bubble > 0] = 255

            pil_canvas = Image.fromarray(canvas)
            draw = ImageDraw.Draw(pil_canvas)
            draw.text((bubble_cx - header_w // 2, bubble_cy - bubble_h // 2 + 10), header_text, font=header_font, fill=color)

            y_offset = bubble_cy - (len(lines) * 14) + 12
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_w = bbox[2] - bbox[0]
                draw.text((bubble_cx - text_w // 2, y_offset), line, font=font, fill=(0, 0, 0))
                y_offset += line_spacing

            canvas = np.array(pil_canvas)

        panel_pil = cv2_to_pil(canvas)
        processed_panel_images.append(panel_pil)

    # --- Compositing Panels into A4 Manga Page ---
    print(f"\nCompositing {len(processed_panel_images)} panel images into A4 Manga Page layout...")
    manga_page = create_manga_page(
        images=processed_panel_images,
        frames=manga_frames,
        width=page_width,
        height=page_height,
        bg_color="white"
    )

    final_output_path = os.path.join(settings.OUTPUT_DIR, output_page_name)
    manga_page.save(final_output_path)
    print(f"\n[COMPLETE] Master Manga Page generated successfully at: {final_output_path}")

    return os.path.abspath(final_output_path)

def generate_full_video_manga_volume(
    video: str,
    num_pages: int = 3,
    num_frames_per_page: int = 7,
    output_pdf_name: str = "final_manga_volume.pdf",
    page_width: int = 1000,
    page_height: int = 1400
) -> str:
    """Master end-to-end prototype pipeline: converts a full video into a multi-page manga volume PDF.

    Args:
        video (str): Path to input video file or video object path.
        num_pages (int): Number of manga pages to generate (default: 3).
        num_frames_per_page (int): Number of panels/frames per manga page (default: 7).
        output_pdf_name (str): Filename for final PDF document (default: 'final_manga_volume.pdf').
        page_width (int): Width for manga page canvas (default: 1000).
        page_height (int): Height for manga page canvas (default: 1400).

    Returns:
        str: Absolute path to the generated multi-page PDF document.
    """
    video_path = str(video)
    print("=" * 60)
    print(f"[START] Generating Fast Multi-Page Manga Volume ({num_pages} Pages) for: {video_path}")
    print("=" * 60)

    print(f"\nRunning single full-video Speech-to-Text and Diarization pass...")
    audio_path, _ = split_video_audio(video_path)
    stt_result = speech2text(audio_path)
    all_speech_segments = stt_result.get("segments", [])
    print(f" -> Precomputed full video speech segments: {len(all_speech_segments)} segments.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    video_duration = total_frames / fps
    cap.release()

    page_duration = video_duration / float(num_pages)
    generated_page_paths = []

    for page_idx in range(num_pages):
        t_start = page_idx * page_duration
        t_end = (page_idx + 1) * page_duration
        page_name = f"manga_page_{page_idx + 1}.png"
        print(f"\n---> [Page {page_idx + 1}/{num_pages}] Processing video section t = {t_start:.1f}s to {t_end:.1f}s...")

        page_path = generate_video_manga_page(
            video=video_path,
            num_frames=num_frames_per_page,
            output_page_name=page_name,
            page_width=page_width,
            page_height=page_height,
            time_range=(t_start, t_end),
            precomputed_speech_segments=all_speech_segments
        )
        generated_page_paths.append(page_path)

    final_pdf_path = os.path.join(settings.OUTPUT_DIR, output_pdf_name)
    save_manga_pages_to_pdf(generated_page_paths, final_pdf_path)

    print("\n" + "=" * 60)
    print(f"[COMPLETE] Fast Multi-Page Manga Volume PDF created: {final_pdf_path}")
    print("=" * 60)
    return final_pdf_path

def process_video_to_manga_volume(
    video_path: str,
    num_frames_per_page: int = 7,
    stylize_style: str = "c",
    language: str = "en",
    output_pdf_name: str = None,
    page_width: int = 1000,
    page_height: int = 1400,
    seed: int = None,
    progress_callback = None
) -> dict:
    """Master pipeline orchestrator converting a video into a multi-page manga PDF volume.

    Executes Audio Extraction -> STT/Diarization -> Scene-Aware Keyframe Extraction ->
    Timestamp Alignment -> Multi-Page Speech Bubble Compositing -> PDF Volume Export.

    Args:
        video_path (str): Path to input video file (absolute or relative to settings.INPUT_DIR).
        num_frames_per_page (int): Target panels per page (default: 7).
        stylize_style (str): Artistic filter identifier ('a', 'b', or 'c').
        language (str): STT transcription language code ('en', 'vi', etc.).
        output_pdf_name (str, optional): Filename for output PDF. Defaults to '<video_name>_manga_volume.pdf'.
    """
    def report(msg):
        print(msg)
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass

    if not os.path.isabs(video_path):
        potential_path = os.path.join(settings.INPUT_DIR, video_path)
        if os.path.exists(potential_path):
            video_path = potential_path

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    if output_pdf_name is None:
        output_pdf_name = f"{base_name}_manga.pdf"

    # Step 1: Audio extraction & Speech STT/Diarization
    report("[1/5] Extracting 16kHz mono WAV audio and soundless video...")
    audio_path, video_clean_path = split_video_audio(video_path)

    report("[2/5] Running single-pass Speech-to-Text and ECAPA-TDNN Speaker Diarization...")
    speech_res = speech2text(os.path.basename(audio_path), language=language)
    speech_segments = speech_res.get("segments", [])
    full_transcript = speech_res.get("text", "")

    # Step 2: Scene-aware keyframe extraction with 7s max scene gap constraint
    report("[3/5] Extracting scene-aware keyframes (7.0s max scene gap constraint)...")
    from modules.frame.video_processor import extract_keyframes
    keyframes = extract_keyframes(
        video_path=video_path,
        max_scene_gap_sec=7.0,
        detect_scenes=True,
        scene_threshold=0.35,
        min_clarity=True
    )

    # Step 3: Keyframe & Dialogue Timestamp Alignment
    report(f"[4/5] Aligning {len(keyframes)} keyframe timestamps with {len(speech_segments)} speech turns...")
    from modules.frame.timestamp_matcher import match_keyframes_with_dialogue
    frame_dialogue_pairs = match_keyframes_with_dialogue(keyframes, speech_segments)

    # Step 4: Multi-Page Speech Bubble Compositing
    from modules.frame.manga_processor import create_manga_page_with_dialogue, save_manga_pages_to_pdf

    page_images = []
    page_urls = []
    global_speaker_map = {}
    total_pages = max(1, (len(frame_dialogue_pairs) + num_frames_per_page - 1) // num_frames_per_page)

    for i in range(0, len(frame_dialogue_pairs), num_frames_per_page):
        page_num = len(page_images) + 1
        report(f"[5/5] Compositing Manga Page {page_num} of {total_pages} (Mask2Former face protection & speaker alignment)...")
        chunk_pairs = frame_dialogue_pairs[i:i + num_frames_per_page]
        layout_seed = (seed + i) if seed is not None else None
        page_pil = create_manga_page_with_dialogue(
            frame_dialogue_pairs=chunk_pairs,
            stylize_style=stylize_style,
            width=page_width,
            height=page_height,
            enable_bubbles=True,
            seed=layout_seed,
            global_speaker_map=global_speaker_map
        )

        page_filename = f"{base_name}_page_{page_num:03d}.png"
        page_save_path = os.path.join(settings.OUTPUT_DIR, page_filename)
        page_pil.save(page_save_path)

        page_images.append(page_save_path)
        page_urls.append(f"/output/{page_filename}")

    # Unload Mask2Former and clean memory to prevent OOM
    try:
        from modules.frame.manga_processor import get_segmenter
        get_segmenter().unload()
    except Exception:
        pass
    import gc
    gc.collect()

    # Step 5: Save multi-page PDF volume
    report("Compiling multi-page manga volume PDF...")
    pdf_save_path = os.path.join(settings.OUTPUT_DIR, output_pdf_name)
    save_manga_pages_to_pdf(page_images, pdf_save_path)

    pdf_rel = os.path.relpath(pdf_save_path, settings.OUTPUT_DIR).replace("\\", "/")

    return {
        "video_url": f"/output/{os.path.basename(video_path)}",
        "audio_url": f"/output/{os.path.basename(audio_path)}" if 'audio_path' in locals() and os.path.exists(audio_path) else "",
        "pdf_path": os.path.abspath(pdf_save_path),
        "pdf_url": f"/output/{pdf_rel}",
        "manga_urls": page_urls,
        "total_pages": len(page_urls),
        "total_keyframes": len(keyframes),
        "text": full_transcript,
        "segments": speech_segments
    }

if __name__ == "__main__":
    sample_video = os.path.join(settings.BASE_DIR, "data", "video", "sample_vid.mp4")
    if os.path.exists(sample_video):
        print(f"Running master prototype generation for video: {sample_video}")
        pdf_path = generate_full_video_manga_volume(
            video=sample_video,
            num_pages=3,
            num_frames_per_page=7,
            output_pdf_name="final_manga_volume.pdf"
        )
        print(f"Prototype finished! Final PDF output saved at: {pdf_path}")
