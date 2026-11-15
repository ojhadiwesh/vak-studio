"""Visual style presets. A project picks one with "style": "<id>" (or {"preset": id, "block": extra}),
and `python -m vak run project.json --style <id>` switches it without editing the project.
Images for each style live in images/<style>/<scene>.png, so several styles can coexist
and the film is written as <out>_<style>.mp4.

Every preset has an image prompt block, a negative prompt and a motion block for
image-to-video models. The motion block enforces the house rule: faces stay still;
light, cloth, water, smoke and petals move."""

# Wan I2V prompt = motion + camera (see docs/MODEL_PRACTICES.md). This is the "what stays still" tail.
MOTION_RULE = "Faces stay stable and natural, with no morphing."   # pace is set per scene; a global "slowly" made clips look like stills
DEFAULT_CAMERA = "Fixed camera."
NEGATIVE_BASE = ("text, letters, watermark, logo, signature, extra limbs, extra fingers, deformed hands, "
                 "distorted face, modern clothing, low quality, blurry")
# extra image negatives for painted styles (photoreal styles must not negate "photo")
PAINTED_NEG = "cartoon, 3d render, photo"

PRESETS = {
    "ravi_varma": {
        "name": "Raja Ravi Varma",
        "block": "Traditional Indian devotional oil painting inspired by Raja Ravi Varma, realistic figures, "
                 "rich warm colors, soft golden divine light, fine detail, sacred and serene mood, cinematic composition, 16:9.",
        "motion": "Oil-painting texture preserved.",
    },
    "pahari": {
        "name": "Pahari / Kangra miniature",
        "block": "Pahari Kangra miniature painting, delicate fine brushwork, soft pastel greens, pinks and blues, "
                 "lyrical Himalayan foothill landscape, flowering trees, ornate thin border, 18th-century style, 16:9.",
        "motion": "Flat miniature look preserved, gentle parallax only.",
    },
    "pattachitra": {
        "name": "Odisha Pattachitra",
        "block": "Odisha Pattachitra scroll painting, bold black outlines, flat vivid red, yellow, indigo and white, "
                 "large expressive eyes, intricate floral and geometric borders, cloth texture, 16:9.",
        "motion": "Flat graphic style preserved, no shading changes.",
    },
    "tanjore": {
        "name": "Tanjore (Thanjavur)",
        "block": "Thanjavur Tanjore painting, rich gold leaf relief, deep red and green background, gem-studded ornaments, "
                 "rounded serene faces, arched temple frame, luminous and iconic, 16:9.",
        "motion": "Gold leaf glints slowly as the light moves.",
    },
    "mysore": {
        "name": "Mysore painting",
        "block": "Traditional Mysore painting, gesso work with thin gold, muted elegant colors, graceful figures, "
                 "fine detailed architecture and nature, soft and refined, 16:9.",
        "motion": "Muted palette preserved.",
    },
    "watercolour": {
        "name": "Soft watercolour",
        "block": "Luminous Indian devotional watercolour on textured cream paper, soft wet-in-wet washes, "
                 "warm saffron and gold light, gentle ink linework, serene and airy, 16:9.",
        "motion": "Paper texture preserved; washes bloom softly.",
    },
    # ---- beyond Indian traditions (public-domain movements / generic looks; no living artists or studios) ----
    "byzantine": {
        "name": "Byzantine icon / gold mosaic",
        "block": "Byzantine icon painting and gold mosaic, flat gold-leaf sky, frontal hieratic figures, "
                 "deep lapis blue and crimson robes, tessellated mosaic texture, solemn and luminous, 16:9.",
        "motion": "Mosaic tesserae glint as candlelight moves; the gold ground stays flat.",
    },
    "art_nouveau": {
        "name": "Art Nouveau (Mucha-inspired)",
        "block": "Art Nouveau illustration inspired by Alphonse Mucha, a full-bleed scene with no border or frame, "
                 "flowing curved lines in the clouds, water and mist, soft muted gold, sage and rose palette, "
                 "elegant contour lines, 16:9.",
        "negative": "cartoon, 3d render, photo, decorative border, ornamental frame, arch, roundel, poster layout, floating fabric, drapery ribbons, scarves",   # a frame breaks camera moves
        "motion": "Hair, cloth and flowing ornamental lines sway softly.",
    },
    "ukiyo_e": {
        "name": "Ukiyo-e woodblock print",
        "block": "Japanese ukiyo-e woodblock print in the manner of Hokusai and Hiroshige, flat colour areas, "
                 "Prussian blue and soft vermilion, crisp keyblock outlines, stylised waves and clouds, washi paper grain, 16:9.",
        "motion": "Stylised waves and clouds drift; flat print look preserved.",
    },
    "persian_miniature": {
        "name": "Persian miniature",
        "block": "Persian Safavid miniature painting, jewel-like turquoise, lapis and gold, high horizon, "
                 "intricate patterned textiles and tilework, delicate fine detail, illuminated border, 16:9.",
        "motion": "Flat miniature look preserved; banners and leaves stir lightly.",
    },
    "romantic_oil": {
        "name": "Romantic / Pre-Raphaelite oil",
        "block": "19th-century Romantic and Pre-Raphaelite oil painting in the manner of J. W. Waterhouse, "
                 "luminous glazes, rich detail, dramatic atmospheric skies, poetic natural light, 16:9.",
        "motion": "Oil-painting texture preserved; clouds and light shift slowly.",
    },
    "ink_wash": {
        "name": "East Asian ink wash",
        "block": "East Asian ink wash painting, sumi-e, expressive black ink brushstrokes, misty negative space, "
                 "subtle touches of gold and vermilion, rice-paper texture, meditative and sparse, 16:9.",
        "motion": "Ink mist breathes and drifts across the empty paper.",
        "negative": "cartoon, 3d render, photo, saturated colour",
    },
    "stained_glass": {
        "name": "Stained glass",
        "block": "Luminous stained-glass window, leaded black outlines, jewel-toned translucent glass, "
                 "light glowing through from behind, gothic tracery frame, 16:9.",
        "motion": "Light glows and pulses gently through the coloured glass.",
    },
    "paper_cut": {
        "name": "Layered paper-cut diorama",
        "block": "Layered paper-cut diorama, many cut-paper layers at different depths, soft shadows between layers, "
                 "handcrafted texture, warm backlit glow, miniature theatre feel, 16:9.",
        "motion": "Paper layers shift with gentle parallax.",
        "negative": "photo, flat, blurry",
    },
    # ---- mainstream looks for storybook films (described generically: no studio, film or character is named or imitated) ----
    "anime_painted": {
        "name": "Hand-painted anime",
        "block": "Hand-painted anime film still, soft watercolour backgrounds with lush detailed nature, gentle cel-shaded "
                 "characters with clean expressive linework, warm natural light, nostalgic and peaceful mood, 2D animation, 16:9.",
        "motion": "2D animation look preserved; grass, cloth and clouds drift gently.",
        "negative": "photo, photorealistic, 3d render, harsh shadows",
    },
    "animated_3d": {
        "name": "3D animated feature",
        "block": "Stylized 3D animated feature film still, soft rounded shapes, expressive friendly faces, warm cinematic "
                 "lighting with soft global illumination, rich colour, gentle depth of field, family film, 16:9.",
        "motion": "Soft 3D animation look preserved; light and cloth move gently.",
        "negative": "photo, photorealistic, 2d, flat, sketch, uncanny",
    },
    "indian_comic": {
        "name": "Indian comic book",
        "block": "Classic Indian mythology comic book panel, bold confident ink outlines, flat vintage print colours with "
                 "halftone texture, dramatic composition, expressive figures, 1970s comic art, no speech bubbles, 16:9.",
        "motion": "Print texture preserved; flat colours stay flat.",
        "negative": "photo, 3d render, speech bubble, caption box, lettering",
    },
    "storybook": {
        "name": "Storybook watercolour",
        "block": "Children's picture-book illustration, delicate watercolour and coloured pencil on textured paper, soft edges, "
                 "warm gentle palette, whimsical and tender, lots of white space glow, 16:9.",
        "motion": "Paper texture preserved; washes bloom softly.",
        "negative": "photo, 3d render, dark, harsh",
    },
    "claymation": {
        "name": "Claymation",
        "block": "Stop-motion claymation still, handmade plasticine figures with visible fingerprints and texture, miniature "
                 "handcrafted set, soft studio lighting, shallow depth of field, charming and tactile, 16:9.",
        "motion": "Stop-motion feel; small steps of movement.",
        "negative": "photo of real people, 2d, flat illustration, painting",
    },
    "cinematic": {
        "name": "Cinematic photoreal",
        "block": "Cinematic film still, photorealistic, anamorphic 35mm, volumetric golden-hour light, "
                 "shallow depth of field, rich film grain, epic and reverent, 16:9.",
        "motion": "Volumetric light and dust drift through the air.",
        "negative": "cartoon, illustration, painting, 3d render, plastic skin",
    },
    "photoreal": {
        "name": "Photoreal live action",
        "block": "Photorealistic live-action film still, real people with natural skin texture, shot on a cinema camera "
                 "with a 35mm lens, natural motivated light (lamps, fire, sun), shallow depth of field, subtle film grain, "
                 "historically accurate ancient Indian setting, full-bleed frame, 16:9.",
        "motion": "Natural, realistic movement.",
        "negative": "cartoon, illustration, painting, anime, 3d render, CGI, plastic skin, waxy face, oversaturated, "
                    "decorative border, frame, text, modern objects, floating fabric",
    },
    # ---- code-animation styles (option B): drawn by assets/anim/<id>.js from anim_plan.json, no AI images ----
    # ---- live styles: drawn in the viewer's browser (web/static/vakfx.js) from the audio and word timings; no render ----
    "nada": {               # cymatics: sand on a bronze plate shaped by the voice's pitch, brightness and loudness
        "name": "Nāda · cymatics", "kind": "live", "block": "", "motion": "",
    },
    "gold": {               # pigment flowing in dark water, stirred by the voice, a bloom of colour on every word
        "name": "Liquid gold", "kind": "live", "block": "", "motion": "",
    },
    "kana": {               # particle morph: grains of light form ॐ, then each sung word, then the deity's symbol (vakfx_motion.js)
        "name": "Kaṇa · particles of light", "kind": "live", "block": "", "motion": "",
    },
    "agni": {               # a havan fire; embers rise from it and gather into each sung word
        "name": "Agni · sacred fire", "kind": "live", "block": "", "motion": "",
    },
    "dhupa": {              # incense smoke in a dark shrine; each word forms in the smoke
        "name": "Dhūpa · incense smoke", "kind": "live", "block": "", "motion": "",
    },
    "akasha": {             # night sky: each word a constellation over stardust; the sun rises at the end
        "name": "Ākāśa · night sky", "kind": "live", "block": "", "motion": "",
    },
    "yantra": {             # figure-free: sacred geometry + the deity's symbols + each sung word written in light
        "name": "Yantra + Akshara", "kind": "animation",
        "block": "", "motion": "",
    },
    "shadow_puppet": {
        "name": "Shadow puppets (tholu bommalata)", "kind": "animation",
        "block": "", "motion": "",
    },
    "silhouette": {
        "name": "Silhouette paper-cut + sacred-geometry finale", "kind": "animation",
        "block": "", "motion": "",
    },
    "pattachitra_anim": {   # same plans as silhouette, drawn with GPU-painted Pattachitra pieces (art/pattachitra/)
        "name": "Pattachitra painted cut-outs + sacred-geometry finale", "kind": "animation",
        "block": "", "motion": "",
    },
}
DEFAULT = "ravi_varma"


def resolve(style, override=None):
    """Return {id, name, block, negative, motion} from a project's style field and an optional CLI override."""
    extra = ""
    if isinstance(style, dict):
        sid, extra = style.get("preset"), style.get("block", "")
        if not sid and extra:                       # older projects: a free-text block only
            return {"id": "custom", "name": "Custom", "block": extra, "negative": f"{NEGATIVE_BASE}, {PAINTED_NEG}", "motion": MOTION_RULE}
    else:
        sid = style
    sid = override or sid or DEFAULT
    if sid not in PRESETS:
        raise SystemExit(f"unknown style '{sid}'. Choose one of: {', '.join(PRESETS)}")
    p = PRESETS[sid]
    return {"id": sid, "name": p["name"], "kind": p.get("kind", "ai"), "block": f"{p['block']} {extra}".strip(),
            "negative": f"{NEGATIVE_BASE}, {p.get('negative', PAINTED_NEG)}", "motion": f"{MOTION_RULE} {p['motion']}"}
