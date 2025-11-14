import os
import json
import re
import whisper
import openai
import textwrap
import subprocess
import numpy as np
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from moviepy.config import change_settings
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

# === CONFIGURATION MOVIEPY ===
change_settings({
    "IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
})

# === CONFIG ===
openai.api_key = os.getenv("OPENAI_API_KEY")
TEMP_AUDIO = "temp_audio.wav"
OUTPUT_VIDEO = "video_kanji_expliquee.mp4"
OUTPUT_PDF = "kanji_vocabulaire.pdf"

# === 1. EXTRACTION AUDIO ===
def extraire_audio(video_path):
    subprocess.run([
        "ffmpeg", "-i", video_path, "-ar", "16000", "-ac", "1", TEMP_AUDIO, "-y"
    ])
    print("✅ Audio extrait :", TEMP_AUDIO)

# === 2. TRANSCRIPTION ===
def transcrire_video(audio_file):
    model = whisper.load_model("small")
    print("🎤 Transcription en cours...")
    result = model.transcribe(audio_file, language="ja")
    segments = result.get("segments", [])
    print(f"✅ {len(segments)} segments détectés.")
    return segments

# === 3. EXPLICATION DES KANJI ===
def expliquer_kanji(texte):
    prompt = f"""
あなたは日本語教師であり、YouTube動画で漢字を教えるナレーターです。
次の文に出てくる重要な漢字を最大で3つ選び、それぞれに以下の形式で説明してください：

出力フォーマット（必ず守ってください）：
[
  {{"kanji": "目標", "lecture": "もくひょう", "fr": "objectif"}},
  {{"kanji": "景色", "lecture": "けしき", "fr": "paysage"}}
]

文：「{texte}」
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        texte_gpt = response.choices[0].message.content
        m = re.search(r"\[.*\]", texte_gpt, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        else:
            return []
    except Exception as e:
        print(f"⚠️ Erreur GPT : {e}")
        return []

# === 4. VIDÉO AVEC TEXTE STYLE SOUS-TITRE ===
def generer_video(video_path, segments, explications):
    print("🎬 Génération de la vidéo avec explications de kanji...")
    base_video = VideoFileClip(video_path)
    clips = []

    font_path = r"C:\Windows\Fonts\NotoSansJP-VF.ttf"
    padding = 10       # plus compact
    stroke_width = 2   # contour plus fin

    for seg, exp in zip(segments, explications):
        texte_ja = seg["text"].strip()
        if not texte_ja:
            continue
        start, end = seg["start"], seg["end"]

        if len(texte_ja) > 40:
            texte_ja = texte_ja[:37] + "…"

        # Préparer les lignes
        lignes = [f"🈶 {texte_ja}"]
        if exp:
            for e in exp:
                lignes.append(f"「{e['kanji']}」({e['lecture']}): {e['fr']}")

        # Limite de lignes
        max_lines = 6
        if len(lignes) > max_lines:
            lignes = lignes[:max_lines - 1] + ["(autres kanjis omis...)"]

        # Taille de police fixe petite
        fontsize = 28
        font = ImageFont.truetype(font_path, fontsize)

        # Wrap automatique
        max_text_width = int(base_video.w * 0.85)
        wrapped_lines = []
        for line in lignes:
            chars_per_line = int(max_text_width / (fontsize * 0.8))
            wrapped_lines.extend(textwrap.wrap(line, width=chars_per_line))
        lines = wrapped_lines

        # Calcul des dimensions
        widths = [font.getbbox(line)[2] - font.getbbox(line)[0] for line in lines]
        heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
        max_width = min(max(widths) + padding * 2, base_video.w - 50)
        total_height = sum(heights) + padding * (len(lines) + 1)

        # Image du texte (fond noir semi-transparent)
        img = Image.new("RGBA", (max_width, total_height), (0, 0, 0, 150))
        draw = ImageDraw.Draw(img)
        y = padding
        for line, h in zip(lines, heights):
            draw.text((padding, y), line, font=font, fill="white",
                      stroke_width=stroke_width, stroke_fill="black")
            y += h + padding

        # Position : toujours en bas
        y_position = base_video.h - total_height - 50

        img_array = np.array(img)
        txt_clip = (
            ImageClip(img_array)
            .set_position(("center", y_position))
            .set_start(start)
            .set_end(end + 0.5)
        )
        clips.append(txt_clip)

    final = CompositeVideoClip([base_video] + clips)
    final.write_videofile(OUTPUT_VIDEO, codec="libx264", audio_codec="aac", fps=base_video.fps)
    print(f"✅ Vidéo générée : {OUTPUT_VIDEO}")

# === 5. PDF VOCABULAIRE ===
def generer_pdf(explications):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSansJP", "", r"C:\Windows\Fonts\NotoSansJP-VF.ttf", uni=True)
    pdf.set_font("NotoSansJP", "", 14)
    pdf.cell(0, 10, "📘 Vocabulaire de la vidéo", ln=True)
    pdf.ln(5)

    largeur = 180
    for exp_list in explications:
        for e in exp_list:
            ligne = f"{e['kanji']}（{e['lecture']}）：{e['fr']}"
            pdf.multi_cell(largeur, 8, ligne)
        pdf.ln(2)

    pdf.output(OUTPUT_PDF)
    print(f"✅ PDF généré : {OUTPUT_PDF}")

# === 6. PIPELINE ===
def main(video_path):
    extraire_audio(video_path)
    segments = transcrire_video(TEMP_AUDIO)

    print("🈶 Génération des explications de kanji...")
    explications = [
        expliquer_kanji(seg["text"].strip()) if seg["text"].strip() else [] for seg in segments
    ]

    generer_video(video_path, segments, explications)
    generer_pdf(explications)

# === 7. EXÉCUTION ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Utilisation : python video_kanji_pdf.py <fichier_video>")
    else:
        main(sys.argv[1])
