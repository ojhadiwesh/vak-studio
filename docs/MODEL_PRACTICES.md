# How we use the models (best practices)

Working notes for the GPU pipeline: Qwen-Image makes a keyframe, then Wan 2.2 I2V-A14B animates it.
Sources are listed at the end. **Treat every number here as a starting point until our own test matrix
(bottom of this file) confirms it on our footage.**

## 1. Keyframe: Qwen-Image 2512

The keyframe decides the whole look of a clip. Wan only animates what it is given, so most quality work
happens at this stage.

- **Structure the prompt: subject first, then setting, light and style.** Front-load the main figure and its
  pose. Our prompt order is style block, then scene description, then character text. Putting the
  subject first is something to test (T5).
- **Qwen-Image honours negative prompts.** Our base negative suppresses text, watermarks, extra limbs and
  deformed hands. Each style also needs its *own* exclusions. For example, "photo" must not be negated when
  the style is photoreal (fixed: styles now carry per-style negatives).
- **CFG:** we use 2.5 at 30 steps (the ComfyUI template). Guides suggest 4–5, warning that above ~5 contrast
  and artefacts rise. Test 2.5 vs 4 (T4).
- **Counting is weak.** "Seven horses" usually comes out as 4–6. Ask for a fanned-out, staggered team, and
  check every take. Fix by retaking or editing with Qwen-Image-Edit; don't rely on the prompt.
- **Iconography is checked by a human every time:** number of arms and horses, attributes (lotus, conch,
  discus), mudras, the colour of a deity.
- **Composition for video:** leave room for motion. Plan an empty sky or water area that can animate, and
  keep the main faces away from the frame edges, where camera moves distort most.

## 2. Clip: Wan 2.2 I2V-A14B

### Prompt = motion + camera (do not re-describe the image)

The image already fixes subject, scene and style. The official Alibaba guide's image-to-video formula is
**"Motion + Camera movement"**. Describing what is already visible wastes the prompt and invites drift.

A good clip prompt has four parts:
1. **One primary motion**, with amplitude and speed: "mist drifts slowly across the river".
   A second, *ambient* motion is fine ("candle flames flicker"). Three or more actions come out jerky or cut short.
2. **One camera move**, named with standard terms: `static shot / fixed camera`, `camera slowly pushes in`,
   `camera pulls back`, `camera pans left/right`, `camera tilts up`, `slow orbit` (keep orbits under 45°).
   Never chain camera moves inside one clip.
3. **Pace word:** "slowly", "gently", "very subtle" for our reverent register.
4. **What must not move:** "the figure stays perfectly still, face unchanged" (our house rule).

Keep it to two or three sentences. Wan weights the start of the prompt most, so put the primary motion first.

Choose the camera move for its meaning:

| Move | Effect | Use for |
|---|---|---|
| fixed camera | stillness, focus | meditation, deity darshan |
| slow push in | intimacy, rising devotion | approaching a face or the heart |
| slow pull back | reveal, scale | the three worlds, cosmic scenes |
| slow tilt up | ascent, awe | from the earth up to the sun or deity |
| pan | travel, continuity | landscapes, processions |

### What Wan cannot do (avoid)
- Scene cuts inside a clip (one clip is one continuous shot).
- Legible text, lip sync to specific words, named real people.
- Long or complex action sequences.
- Big motion on faces and hands. Faces morph, so keep them still and animate light, cloth, water, smoke and petals.

### Negative prompt
Wan's official default negative (Chinese) suppresses static or motionless frames, over-saturation,
overexposure, blur, subtitles, extra fingers, poorly drawn hands and faces, deformed limbs, three legs,
crowds and walking backwards. **It also negates "style, artwork, painting, picture" (风格，作品，画作，画面),
which works against our painted styles.** We use the official list with those four words removed,
plus our own terms (morphing face, flicker, camera shake).

### Settings
| Setting | Official repo | ComfyUI template (ours today) |
|---|---|---|
| Steps | 40 | 20 |
| Shift | 5.0 | 8.0 |
| CFG (high, low) | 3.5, 3.5 | 3.5 |
| High→low expert switch | boundary 0.900 (≈ step 14 of 40 at shift 5) | half the steps (≈ the same boundary at shift 8) |
| Frames / fps | 81 @ 16 fps (≈ 5 s) | same |
| Resolution | 480p or 720p (we use 1280×720) | same |

- **Draft mode** (lightx2v 4-step LoRAs, CFG 1) is about 5× faster. Use it to judge motion and camera, never
  for finals. LoRAs weaken prompt adherence.
- Lower shift (3–5) keeps more of the input image; higher shift allows more motion. Test 5 vs 8 (T2).
- Clips are 5 s; our scenes run 4–6 s. Longer scenes are made by chaining a second clip from the last frame,
  or by slowing the playthrough (motion.py already does slow-mo without ping-pong).

## 3. Lessons from our first clips (Gāyatrī, 2026-11-13)

Seven draft clips (lightx2v 4-step, 1280×720, 81 frames) on five keyframes. These are observations, not a
controlled test, but each one was clear.

| What we saw | Why | Rule |
|---|---|---|
| G02 sunrise, G00 night, G03 seated figure: stable, no drift, figure did not move | Prompt was one motion + one camera + "stays still" (section 2) | Keep the formula. It works. |
| G04 lotus + diya: a hand reached in for the diya | An object that people place (lamp, diya, flower offering) implies the person who places it | Write "No people or hands appear; nothing enters the frame." Fixed it on the first retry. |
| G01 pre-dawn: two hands, then two raised palms toward the dawn, even after that sentence | Camera tilting up from ghat stones in the foreground reads as a first-person view, and raised palms to the rising sun is the arghya gesture Wan associates with dawn worship | For empty scenes with foreground ground, use a **fixed camera**, not a tilt. Fixed camera cured it. |
| The negative prompt did not stop the hands in draft mode | **Draft runs at CFG 1, where the negative prompt has no effect at all.** Only the positive prompt steers a draft | In drafts, say what must not appear in the *positive* prompt. Judge negative-prompt changes only at final quality (CFG 3.5). |
| Night river at "Fixed camera": stars, mist and the lamp flame all moved gently | Wan adds ambient motion by itself | A fixed camera is not a frozen picture; it is our safest default. |

| The film looked like still pictures that barely move | Every prompt said "slowly and gently" and "stays still", we slowed 5 s clips 2×, and filled 9–12 s shots with a zoom on the last frame | **Real speed, short shots.** One shot ≤ ~4.3 s (a clip is 5.06 s, minus the 0.8 s crossfade), cut often, `slow` ≈ 1. Give each shot a real action (walking, wading, pouring water, birds taking off, a lamp floating away) and a moving camera. Keep faces stable, not the whole picture. |

| Art Nouveau lamp shot: a pink fabric ribbon at the frame edge became a woman looking at the lamp | The style asked for flowing lines "in the cloth", so the keyframe had loose drapery; Wan reads drapery as someone's clothes and adds the wearer | In empty scenes, no loose fabric in the keyframe. Style text says lines in clouds, water and mist only; negative has "floating fabric, drapery ribbons". |
| Image-Edit reference shots copied the anchor's composition (close-up came out as the anchor again) | Qwen-Image-Edit keeps layout as well as identity | Use `reference` only where the character is clearly seen; draw hands-only or tiny-figure shots fresh. |

| Final V01: an ornamental curl at the frame edge became a second person walking in | Same as drapery: Wan turns ambiguous shapes at the frame edge into people, worst with a moving camera | Keep frame edges plain in the keyframe. Rescue: crop the clip (we cropped to the left 78%). |
| Final V03: the camera rose so far the lamp left the frame | "Camera rises slowly upward, revealing the sky" was obeyed fully at final quality | Finals follow camera moves more strongly than drafts; keep the subject in frame ("the camera rises a little, keeping the lamp in view"). |

Checks that caught these: a 4-frame strip (frames 0, 27, 54, 80) of every clip before it goes in the film.
Things appear late in a clip, so always look at the last frame.

**T7 answered (draft vs final):** the G01 prompt with the camera tilting up gave hands in two drafts; the same prompt at final quality
(20 steps, CFG 3.5, negative active) came out clean, with the camera move intact. Drafts are fine for checking composition and timing,
not for judging what the model will add.

Timing on the RTX PRO 6000: keyframe ≈ 34 s; draft clip ≈ 93 s (123 s with the first model load); final 20-step clip ≈ 13 min
(≈ $0.60 at $2.69/h). The RunPod proxy occasionally drops a status request on long jobs; `comfy.py` now retries instead of failing.

Still open: T2–T6 below.

## 4. Test matrix (on the pod, one keyframe, fixed seed)

| Test | Variable | Variants | Judge by |
|---|---|---|---|
| T1 | Prompt form | current (scene + rule + title) vs motion+camera formula | drift, motion quality |
| T2 | Shift | 5 vs 8 | fidelity to keyframe vs liveliness |
| T3 | Steps | 20 vs 40 | detail, artefacts (time ×2) |
| T4 | Keyframe CFG | 2.5 vs 4 | crispness, artefacts |
| T5 | Camera move | fixed / push in / tilt up | which reads as reverent |
| T6 | Negative | ours vs official minus "painting" words | painted texture kept |
| T7 | Draft vs final | lightx2v 4-step vs 20-step | is draft a fair preview? |

Cost: a final 720p clip is ≈ 3–5 min of GPU, draft ≈ 1 min, so the whole matrix is roughly $1–2.

## Sources
- Alibaba Cloud, text-to-video / image-to-video prompt guide (official): https://www.alibabacloud.com/help/en/model-studio/text-to-video-prompt
- Wan 2.2 repo and configs (`wan/configs/wan_i2v_A14B.py`, `shared_config.py`): https://github.com/Wan-Video/Wan2.2
- lightx2v distill LoRAs: https://huggingface.co/lightx2v/Wan2.2-Distill-Loras
- Community guides (starting points only): https://www.veed.io/learn/wan-2-2-prompting-guide ,
  https://unifically.com/blogs/wan-2.2-image-to-video-prompt-guide , https://blog.segmind.com/qwen-image-prompt-parameter-guide/ ,
  https://stable-diffusion-art.com/qwen-image/
