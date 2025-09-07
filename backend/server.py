import base64
import os
import uuid
from typing import Literal, Optional, Dict, Any

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from io import BytesIO
import random

# Optional deps for regulated cropping (OpenCV)
try:
    import numpy as np  # type: ignore
    import cv2  # type: ignore
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False
    np = None  # type: ignore
    cv2 = None  # type: ignore


import logging

logger = logging.getLogger("ai_portrait_studio")
logger.setLevel(logging.INFO)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Control how many variants to generate per request (single-subject path)
try:
    SHOT_COUNT = max(1, int(os.getenv("MULTI_SHOT_COUNT", "1")))
except Exception:
    SHOT_COUNT = 1
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash-image-preview:generateContent"
)


class GenerateBody(BaseModel):
    theme: Literal[
        "resume",
        "passport",
        "memory",
        "fantasy_real",
        "fantasy_anime",
        "model",
        "kpop",
        "actor",
        "travel",
        "anime",
        "activity",
        "profession",
        # New themes
        "wedding",
        "graduation",
        "traditional",  # Hanbok / classic studio
        "retro",
        "sports",
        "musician",
        "film",
        "lookbook",
        "makeover",
        "meme",
        # Additional themes
        "animal",
        "lifestage",
        "timetravel",
        "cosmos",
        # Newly added
        "aerial_set",
        "baby_studio",
    ]
    image: str  # base64-encoded image (PNG or JPEG)
    mime_type: Optional[str] = None  # e.g. image/png, image/jpeg
    options: Optional[Dict[str, Any]] = None  # theme-specific options


class CompositeBody(BaseModel):
    # User portrait to cast into reference image
    user_image: str
    user_mime_type: Optional[str] = None
    # Reference scene/character/poster to merge into
    ref_image: str
    ref_mime_type: Optional[str] = None
    # Optional role/style hints (freeform)
    hint: Optional[str] = None


def _fantasy_scenario() -> str:
    roles = [
        "elven archer in a moonlit forest",
        "royal knight in ornate plate armor",
        "mystic mage casting glowing runes",
        "dragon rider above stormy cliffs",
        "forest druid with luminous spirits",
        "desert wanderer with flowing cloak",
        "viking shield-bearer by the fjord",
        "angelic guardian with ethereal light",
        "shadow rogue on a rain-soaked rooftop",
        "paladin in a cathedral of light",
        "steampunk airship captain on deck",
        "fae monarch in a bioluminescent grove",
        "samurai warrior under cherry blossoms",
        "sorcerer with arcane library backdrop",
        "ranger in misty highlands",
    ]
    styles = [
        "cinematic key art, volumetric lighting, subsurface scattering",
        "hyper-detailed concept art, rim light, depth haze",
        "photorealistic fantasy portrait, soft diffusion, 4k",
        "dramatic chiaroscuro lighting, filmic color grade",
        "epic fantasy illustration, god rays, fine fabrics",
    ]
    lenses = [
        "85mm portrait lens, f/2.8",
        "105mm portrait lens, f/2.5",
        "70mm, f/2.8, shallow depth of field",
    ]
    role = random.choice(roles)
    style = random.choice(styles)
    lens = random.choice(lenses)
    return f"Theme: {role}. Visual style: {style}. Camera: {lens}."


def _model_scenario() -> str:
    categories = [
        # Classic editorial / fashion
        (
            "editorial runway model", 
            "sleek tailored suit or couture outfit, clean lines",
            "studio cyclorama or minimalist set",
            "85mm lens, f/4, controlled softboxes, rim light"
        ),
        (
            "magazine cover model",
            "sharp suit or chic dress, sophisticated styling",
            "colored seamless backdrop with subtle gradient",
            "beauty dish key light + fill, crisp contrast"
        ),
        (
            "luxury lifestyle model",
            "black tuxedo or elegant evening wear",
            "night city lights bokeh or luxury interior",
            "50mm lens, f/2, cinematic color grade"
        ),
        # Character-like but realistic
        (
            "James Bond-esque action portrait",
            "tuxedo or slim-fit suit, polished shoes",
            "dramatic moody set, subtle fog, spotlight",
            "cinematic key art lighting, rim + kicker light"
        ),
        (
            "automotive show model",
            "sleek formal wear or premium smart-casual",
            "beside a sports car in an indoor expo",
            "wide-to-tele mix, glossy reflections, HDR control"
        ),
        (
            "documentary poster figure",
            "neat smart casual, minimal accessories",
            "text-safe negative space composition",
            "soft Rembrandt lighting, subdued palette"
        ),
        (
            "textbook cover figure",
            "clean professional attire",
            "academic setting or neutral graphic backdrop",
            "even soft light, high legibility"
        ),
    ]
    subj, attire, scene, camera = random.choice(categories)
    return (
        f"Full-body {subj}. Attire: {attire}. Scene: {scene}. Camera/Light: {camera}."
    )


def _kpop_scenario() -> str:
    concepts = [
        ("idol photocard studio portrait", "sleek stage-inspired fashion", "pastel seamless backdrop",
         "beauty dish key + soft fill, glossy highlights"),
        ("idol MV set still", "trendsetting streetwear with layered accessories", "neon-lit urban alley",
         "cinematic neon rims, shallow depth of field"),
        ("press photoshoot", "chic monochrome suit with subtle jewelry", "clean cyclorama studio",
         "softboxes left/right, subtle hair light"),
        ("concert backstage portrait", "stylized performance outfit", "backstage with bokeh lights",
         "warm key, practical bokeh, filmic grade"),
        ("fashion magazine spread", "avant-garde idol styling", "color gradient seamless",
         "high-key soft light, crisp contrast"),
    ]
    subj, attire, scene, light = random.choice(concepts)
    return f"{subj}. Attire: {attire}. Scene: {scene}. Lighting: {light}."


def _actor_scenario() -> str:
    sets = [
        ("red carpet portrait", "tailored tuxedo or elegant suit", "step-and-repeat backdrop",
         "flash key with soft fill, true skin tones"),
        ("cinematic headshot", "smart casual with texture", "moody studio with negative fill",
         "Rembrandt lighting, subtle kicker, cinematic grade"),
        ("movie poster still", "character wardrobe (clean, realistic)", "dramatic set with depth haze",
         "key + rim + background practicals"),
        ("press junket portrait", "polished blazer with simple shirt", "neutral hotel backdrop",
         "soft key, clean background, balanced contrast"),
    ]
    subj, attire, scene, light = random.choice(sets)
    return f"{subj}. Attire: {attire}. Scene: {scene}. Lighting: {light}."


def _travel_scenario() -> str:
    places = [
        ("Paris, near the Eiffel Tower viewpoint", "street smart-casual", "golden hour with soft clouds"),
        ("Tokyo, Shibuya crossing", "modern casual", "night neon lights and motion bokeh"),
        ("New York City skyline lookout", "smart streetwear", "sunset rim light, city bokeh"),
        ("Santorini cliffside walkway", "light summer outfit", "bright daylight, blue-white palette"),
        ("Seoul, Bukchon Hanok Village street", "neat casual", "soft afternoon light, warm tones"),
        ("Sahara desert dunes", "light breathable outfit", "low sun, long shadows, warm highlights"),
        ("Swiss Alps lakeside", "outdoor smart casual", "clear daylight, crisp cool tones"),
    ]
    place, attire, light = random.choice(places)
    return f"Location: {place}. Outfit: {attire}. Lighting: {light}."


def _anime_style() -> str:
    styles = [
        "modern digital anime, vibrant lighting, clean gradients",
        "soft watercolor anime, pastel palette, delicate linework",
        "retro 1990s cel-shaded anime, bold lines, limited palette",
        "manga black-and-white screentone style, precise hatching",
        "webtoon clean line style, soft shading, high key",
        "semi-realistic anime portrait, painterly shading, detailed eyes",
    ]
    return random.choice(styles)


def _activity_scenario() -> str:
    rides = [
        ("wooden hypercoaster drop", "wind-swept hair, safety harness visible", "motion blur rails, daylight"),
        ("steel inverted coaster loop", "secure over-shoulder restraints", "dynamic camera tilt, blue sky"),
        ("retro carousel ride", "elegant casual outfit", "warm bulbs, bokeh lights, golden hour"),
        ("futuristic indoor coaster", "sporty casual", "neon tunnel, long exposure streaks"),
        ("cinematic planet-themed dark ride", "neat attire", "starfield projections, rim light"),
    ]
    adventure = [
        ("tandem skydiving freefall", "goggles and jumpsuit", "clouds backdrop, wind motion, bright daylight"),
        ("paragliding over coastline", "light windbreaker", "ocean and cliffs, soft haze"),
        ("bungee jump mid-air", "secure ankle/body harness", "bridge structure above, dramatic perspective"),
        ("zipline through forest", "helmet and gloves", "tree canopy blur, sunlight shafts"),
    ]
    watersports = [
        ("surfing a breaking wave", "wetsuit", "spray droplets frozen, sun glint"),
        ("stand-up paddle on lake", "sport casual", "calm water reflections, mountains"),
        ("jetski splash turn", "life vest", "dynamic spray, horizon line"),
        ("scuba diving portrait", "mask and regulator", "clear blue water, bubbles, fish"),
    ]
    winter = [
        ("snowboard jump", "goggles and winter gear", "snow spray, backlit sun"),
        ("downhill skiing", "helmet and poles", "alpine slope, motion blur"),
    ]
    cityfun = [
        ("go-kart racing", "helmet and racing suit", "track cones, panning blur"),
        ("indoor climbing wall", "harness and chalk bag", "holds and textures, side lighting"),
        ("roller skating in neon rink", "retro sporty", "floor reflections, colored lights"),
    ]

    bucket = random.choice([rides, adventure, watersports, winter, cityfun])
    subj, attire, scene = random.choice(bucket)
    lens = random.choice([
        "35mm action lens, f/2.8, fast shutter",
        "24mm wide, f/4, stabilized",
        "50mm, f/2, cinematic motion feel",
    ])
    return f"Activity: {subj}. Outfit/Safety: {attire}. Scene: {scene}. Camera: {lens}."


def _wedding_scenario() -> str:
    scenes = [
        ("white studio", "formal wedding attire appropriate to the subject's gender presentation (e.g., suit/tuxedo or traditional formal wear)", "high-key soft light, clean backdrop"),
        ("garden aisle", "formal wedding attire appropriate to the subject's presentation", "golden hour, warm backlight"),
        ("city rooftop", "formal wedding attire appropriate to the subject's presentation", "blue hour, skyline bokeh"),
        ("beach at sunset", "formal wedding attire appropriate to the subject's presentation", "soft diffusion, pastel sky"),
    ]
    place, attire, light = random.choice(scenes)
    return (
        f"Wedding-style portrait. Scene: {place}. Wardrobe: {attire}. Lighting: {light}. "
        "Do not change the subject's gender or gender expression."
    )


def _graduation_scenario() -> str:
    scenes = [
        ("campus quad", "gown and mortarboard", "soft daylight, shallow depth"),
        ("library hall", "gown and sash", "warm interior, soft key"),
        ("auditorium stage", "gown", "spotlight key, subdued background")
    ]
    place, attire, light = random.choice(scenes)
    return f"Graduation portrait. Scene: {place}. Wardrobe: {attire}. Lighting: {light}."


def _traditional_scenario() -> str:
    scenes = [
        ("hanok studio backdrop", "traditional attire (hanbok) appropriate to the subject's gender presentation (male/female/neutral variant)", "soft studio key, painterly background"),
        ("palace corridor", "traditional attire (hanbok) appropriate to the subject's presentation", "natural soft light, warm tones"),
        ("stone wall by hanok", "traditional attire (hanbok) appropriate to the subject's presentation", "afternoon light, gentle vignette"),
    ]
    place, attire, light = random.choice(scenes)
    return (
        f"Traditional studio portrait. Scene: {place}. Wardrobe: {attire}. Lighting: {light}. "
        "Do not change the subject's gender or gender expression."
    )


def _retro_scenario() -> str:
    styles = [
        "1960s black-and-white studio, classic key + fill",
        "1980s film color, slight halation, vintage grain",
        "1990s magazine look, crisp flash, subtle vignette",
    ]
    return f"Retro style: {random.choice(styles)}."


def _sports_scenario() -> str:
    sets = [
        ("running track", "athletic wear", "strobe key + rim, motion feel"),
        ("indoor gym", "training outfit", "hard light with controlled shadows"),
        ("soccer field", "neutral athletic wear", "golden hour, action posture"),
        ("basketball court", "athletic wear", "court reflections, directional light"),
    ]
    place, attire, light = random.choice(sets)
    return f"Sports portrait. Scene: {place}. Wardrobe: {attire}. Lighting: {light}."


def _musician_scenario() -> str:
    sets = [
        ("stage", "performance outfit", "spotlight key, haze, bokeh"),
        ("rehearsal room", "casual with subtle accessories", "warm practicals, shallow depth"),
        ("recording studio", "neat casual", "soft key, equipment bokeh"),
    ]
    place, attire, light = random.choice(sets)
    return f"Musician portrait. Scene: {place}. Wardrobe: {attire}. Lighting: {light}."


def _film_scenario() -> str:
    genres = [
        "noir with chiaroscuro lighting",
        "romance with warm golden tones",
        "spy thriller with cool cinematic grade",
        "disaster drama with moody atmosphere",
        "heroic drama with strong rim light",
    ]
    return f"Film-genre still: {random.choice(genres)}."


def _lookbook_scenario() -> str:
    seasons = [
        ("spring street", "light layers, pastel palette"),
        ("summer beach boardwalk", "breezy outfit"),
        ("autumn park", "earth tones, layered styling"),
        ("winter city", "coat and scarf, cool palette"),
    ]
    place, attire = random.choice(seasons)
    return f"Seasonal lookbook. Scene: {place}. Wardrobe: {attire}."


def _makeover_style() -> str:
    styles = [
        "business clean grooming, tidy hair, subtle shine",
        "natural glow, soft diffusion, even skin tone",
        "red carpet polish, controlled highlights, elegant contrast",
        "clean beauty studio, high-key, precise detail",
    ]
    return random.choice(styles)


def _meme_scenario() -> str:
    # Playful, surreal, safe collage of multiple elements mixed together
    outfits = [
        "astronaut suit", "chef apron", "tuxedo", "kimono-inspired outfit", "sports training wear",
        "rainbow jacket", "retro tracksuit", "futuristic metallic coat"
    ]
    props = [
        "rubber duck", "glass-like fruit slices", "origami cranes", "neon tubes", "toy blocks",
        "soap bubbles", "slime gel", "chrome spheres", "balloons", "confetti streamers"
    ]
    creatures = [
        "cat", "corgi dog", "goldfish in a bowl", "parrot", "hamster", "turtle"
    ]
    effects = [
        "sparkles", "rainbow light leaks", "soft smoke", "harmless lava-like glow fluid", "floating glitter",
        "gelatin splash", "water splash freeze", "confetti burst"
    ]
    scenes = [
        "sci‑fi light lab", "colorful arcade", "kitchen set", "volcano‑themed studio set",
        "aquarium tunnel", "ice rink with lights"
    ]
    actions = [
        "juggling", "balancing objects", "levitating props (suspended)", "pouring colorful liquid",
        "slice demonstration on transparent board", "blowing bubbles"
    ]

    def pick_many(pool, k):
        k = min(k, len(pool))
        return ", ".join(random.sample(pool, k))

    outfit = random.choice(outfits)
    scene = random.choice(scenes)
    action = random.choice(actions)
    mix_props = pick_many(props, 3)
    mix_creatures = pick_many(creatures, 2)
    mix_fx = pick_many(effects, 2)

    return (
        f"Meme-style surreal collage. Outfit: {outfit}. Scene: {scene}. "
        f"Include multiple items together: props ({mix_props}), friendly creatures ({mix_creatures}), effects ({mix_fx}). "
        f"Action: {action}. Layer elements around the subject with depth and playful composition."
    )


def _animal_scenario() -> str:
    species = [
        ("cat", "subtle feline styling: ear headpiece, soft whisker makeup, warm low-key"),
        ("dog (corgi/retreiver inspired)", "friendly warm styling, soft key, gentle fur-texture accessories"),
        ("fox", "autumn palette, sleek styling, rim light"),
        ("deer", "forest tone backdrop, elegant minimal accessories"),
        ("rabbit", "soft pastel set, clean high-key"),
        ("tiger", "dramatic low-key, orange/black palette, controlled rim"),
        ("bear", "earthy tones, soft diffused key"),
    ]
    sp, style = random.choice(species)
    return f"Animal-inspired portrait: {sp}. Photorealistic styling and accessories, not cartoon; preserve human anatomy; {style}."


def _lifestage_scenario() -> str:
    stages = [
        ("infant", "simulate baby-like facial proportions and skin tone while preserving identity cues; wholesome attire"),
        ("senior", "simulate realistic aging with natural wrinkles and gray hair while preserving identity"),
        ("teen", "youthful features and styling, natural lighting"),
        ("middle-age", "balanced mature features, professional styling"),
    ]
    stage, desc = random.choice(stages)
    return f"Lifestage: {stage}. {desc}. Keep photorealism and dignity."


def _timetravel_scenario() -> str:
    eras = [
        ("Cretaceous period", "lush primeval jungle, distant dinosaurs (non-threatening), warm sunlight"),
        ("Paleolithic era", "rock shelter, firelight, realistic primitive attire"),
        ("Neolithic era", "village setting, earthen tones, woven clothes"),
        ("Ancient civilization", "stone architecture, sunlit dust"),
        ("Near future", "sleek city with neon accents"),
        ("Far future", "clean sci‑fi interior, soft glows"),
    ]
    era, scene = random.choice(eras)
    return f"Time-travel scene: {era}. Environment: {scene}. Photorealistic composition; preserve identity."


def _cosmos_scenario() -> str:
    places = [
        ("Milky Way core vista", "starfield and dust lanes, cinematic color"),
        ("on the Moon", "low gravity stance, regolith ground, Earth in sky"),
        ("Mercury surface", "cratered terrain, hard shadows"),
        ("Venus cloud deck", "soft diffused light through clouds"),
        ("Mars plain", "red soil, rocky horizon"),
        ("Jupiter upper clouds", "colorful bands, safe vantage"),
        ("Saturn ring plane", "icy ring particles, planet backdrop"),
        ("Uranus upper atmosphere", "pale cyan hues"),
        ("Neptune winds", "deep blue, high-altitude clouds"),
        ("Pluto surface", "icy mountains, distant Sun"),
        ("near the Sun (safe composite)", "intense light vignette, protective suit"),
        ("inside a black hole (artistic)", "gravitational lensing visuals, safe surreal depiction"),
    ]
    place, visuals = random.choice(places)
    return f"Cosmos travel: {place}. Visuals: {visuals}. Photorealistic composite look; preserve identity; no text/logos."


def _aerial_set_scenario() -> str:
    angles = [
        "high overhead view (45°)",
        "top‑down drone‑like angle",
        "slightly oblique aerial perspective",
    ]
    details = [
        "film crew with cameras and boom mics",
        "lighting stands and softboxes",
        "track dolly and clapper board",
        "monitor cart and cables",
    ]
    envs = [
        "open studio floor",
        "city street backlot",
        "indoor set with practical lights",
    ]
    return (
        f"An aerial view of the scene as if it was a movie set with a film crew filming. Angle: {random.choice(angles)}. "
        f"Include {random.choice(details)} around the subject on a {random.choice(envs)}. Keep photorealism, preserve the subject's identity."
    )


def _baby_studio_scenario() -> str:
    sets = [
        ("Korean first‑birthday (doljanchi) inspired studio", "hanbok‑style baby outfit", "soft high‑key lighting, pastel backdrop"),
        ("cozy indoor nursery studio", "cute romper and knit hat", "natural window light, warm tones"),
        ("outdoor garden park", "seasonal cute outfit", "golden hour, gentle backlight"),
    ]
    place, attire, light = random.choice(sets)
    return f"Baby portrait studio scene: {place}. Outfit: {attire}. Lighting: {light}. Wholesome and respectful depiction; photorealistic."


def _profession_scenario() -> str:
    # Broad, safe, real-world professions with attire/environment cues (no weapons, no logos)
    roles = [
        ("medical doctor", "clean white coat over scrubs, stethoscope", "modern clinic or hospital corridor"),
        ("surgeon (pre-op portrait)", "surgical scrubs and cap", "operating room background (lights off)"),
        ("nurse", "professional scrubs", "nursing station with soft depth of field"),
        ("scientist", "lab coat, safety goggles", "laboratory benches, glassware bokeh"),
        ("software engineer", "smart casual", "tech office with whiteboards and monitors"),
        ("teacher", "business casual", "classroom with chalkboard or bookshelves"),
        ("university professor", "blazer over shirt", "library stacks background"),
        ("chef", "chef jacket and hat", "stainless steel kitchen pass"),
        ("baker", "apron over shirt", "artisan bakery counter"),
        ("barista", "apron and neat casual", "espresso bar with warm lighting"),
        ("lawyer", "tailored suit", "court building interior or chambers"),
        ("judge (portrait)", "judicial robe", "courtroom backdrop (no text)") ,
        ("entrepreneur / CEO", "formal suit", "modern office skyline view"),
        ("architect", "smart attire, rolled blueprints", "studio with models and plans"),
        ("civil engineer", "PPE: hard hat and safety vest", "construction site (safe zone)"),
        ("pilot", "pilot uniform", "airport terminal window with aircraft bokeh"),
        ("cabin crew", "formal uniform", "aircraft aisle background"),
        ("firefighter (portrait)", "turnout gear (clean), helmet in hand", "station interior, truck bokeh (no fire)"),
        ("police officer (portrait)", "clean dress uniform (no weapons)", "station backdrop (neutral)"),
        ("paramedic", "high-visibility jacket", "ambulance bay background"),
        ("photographer", "smart casual, camera in hand", "studio cyclorama with lights"),
        ("filmmaker", "neat setwear", "film set with light stands (defocused)"),
        ("musician", "performance outfit", "stage with warm spotlights"),
        ("artist / illustrator", "apron, paint marks", "studio with canvases"),
        ("fashion model (catalog)", "seasonal outfit", "minimal backdrop"),
        ("news anchor", "formal suit", "news desk style set (no text)"),
        ("farmer", "workwear and gloves", "field or greenhouse background"),
        ("mechanic", "coveralls, clean hands", "garage with tools (tidy)"),
        ("electrician", "PPE and tool belt", "indoor job site (safe)"),
        ("carpenter", "work apron", "wood workshop with soft sawdust bokeh"),
        ("librarian", "smart casual", "library reading room"),
        ("veterinarian", "scrubs, stethoscope", "clinic with pet kennel (no animals visible)"),
        ("flight attendant", "formal uniform", "jet bridge or cabin"),
        ("pharmacist", "white coat", "pharmacy shelves (defocused)"),
    ]
    role, attire, scene = random.choice(roles)
    light = random.choice([
        "soft key + fill, accurate color",
        "beauty dish key, subtle hair light",
        "high-CRI softboxes, minimal contrast",
        "Rembrandt portrait lighting",
        "clean high-key lighting",
    ])
    return f"Profession: {role}. Wardrobe: {attire}. Environment: {scene}. Lighting: {light}."


def _choose_composition_for_theme(theme: str, options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    # explicit override
    if options and isinstance(options.get("composition"), str):
        comp = options["composition"].lower()
        if comp in {"close", "half", "three_quarter", "full"}:
            if theme not in {"passport", "resume"}:  # ignore for regulated
                return comp
    # composition keys: close, half, three_quarter, full
    def pick(weights):
        keys = list(weights.keys())
        vals = list(weights.values())
        return random.choices(keys, weights=vals, k=1)[0]

    if theme == "passport":
        return None  # regulated
    if theme == "resume":
        return None  # treat resume like regulated headshot; no randomization
    if theme == "memory":
        return pick({"close": 30, "half": 30, "three_quarter": 25, "full": 15})
    if theme in {"model"}:
        return pick({"full": 50, "three_quarter": 35, "half": 10, "close": 5})
    if theme in {"kpop", "actor", "profession", "wedding", "film"}:
        return pick({"three_quarter": 40, "full": 35, "half": 20, "close": 5})
    if theme in {"travel", "activity"}:
        return pick({"full": 50, "three_quarter": 30, "half": 15, "close": 5})
    if theme in {"fantasy_real", "fantasy_anime", "anime", "retro", "meme", "timetravel", "cosmos"}:
        return pick({"full": 30, "three_quarter": 30, "half": 25, "close": 15})
    if theme in {"graduation"}:
        return pick({"half": 45, "three_quarter": 35, "full": 15, "close": 5})
    if theme in {"traditional"}:
        return pick({"half": 40, "three_quarter": 35, "full": 20, "close": 5})
    if theme in {"sports"}:
        return pick({"full": 55, "three_quarter": 30, "half": 10, "close": 5})
    if theme in {"musician"}:
        return pick({"three_quarter": 40, "half": 35, "full": 20, "close": 5})
    if theme in {"lookbook"}:
        return pick({"full": 60, "three_quarter": 30, "half": 8, "close": 2})
    if theme in {"makeover"}:
        return pick({"close": 55, "half": 35, "three_quarter": 8, "full": 2})
    if theme in {"animal"}:
        return pick({"half": 40, "three_quarter": 35, "full": 15, "close": 10})
    if theme in {"lifestage"}:
        return pick({"close": 40, "half": 40, "three_quarter": 15, "full": 5})
    if theme in {"aerial_set"}:
        return pick({"full": 65, "three_quarter": 25, "half": 8, "close": 2})
    if theme in {"baby_studio"}:
        return pick({"half": 45, "three_quarter": 35, "full": 15, "close": 5})
    return pick({"half": 40, "three_quarter": 30, "full": 20, "close": 10})


def _composition_text(comp_key: Optional[str]) -> str:
    if comp_key == "close":
        return " Composition: close-up headshot framing (tight around head and shoulders)."
    if comp_key == "half":
        return " Composition: half-body portrait (chest-up) with comfortable headroom."
    if comp_key == "three_quarter":
        return " Composition: three-quarter portrait (mid-thigh up), balanced headroom and footing."
    if comp_key == "full":
        return " Composition: full-body portrait including feet, ample headroom, natural stance."
    return ""


def build_prompt(theme: str, comp_key: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> str:
    # Keep common guidance neutral about framing/background so action themes aren't forced into studio headshots
    common = (
        "You are a professional photographic retoucher and art director. "
        "Task: Produce a polished, photorealistic image derived from the provided photo while strictly preserving the subject's identity and facial features. "
        "Skin: retain natural texture (no plastic smoothing); even tone; remove only temporary blemishes. Hair tidy and realistic. "
        "Color: accurate white balance and natural contrast. "
        "Prohibitions: absolutely no text or letters or numbers anywhere in the image (including backgrounds and signs), no brand logos, no watermarks, no borders. "
        "Avoid distortions, warping, extra artifacts, or changes to identity."
    )

    if theme == "resume":
        extra = (
            " Style: professional corporate headshot suitable for CV/LinkedIn. "
            "Framing: head-and-shoulders, small breathing room above hair. Eye line near top third. "
            "Expression: confident, approachable; gentle smile ok. Posture: shoulders squared. "
            "Lighting: classic loop or butterfly lighting; soft key + subtle fill; avoid hard shadows under eyes. "
            "Background: seamless neutral (light gray #F2F2F2 to off-white), smooth gradient acceptable. "
            "Retouch: tidy stray hairs, even skin tone while preserving pores, natural teeth/eye brightening, remove temporary blemishes only. "
            "Wardrobe: if casual, upgrade to smart attire or suit jacket and pressed shirt that suits the subject; lint removal, collar alignment. No text/logos."
        )
        gp = (options or {}).get("gender_presentation") if isinstance(options, dict) else None
        if isinstance(gp, str) and gp.lower() in {"male","female","neutral"}:
            extra += f" Subject gender presentation is {gp.lower()}; keep it; wardrobe and grooming should respect this."
    elif theme == "passport":
        extra = (
            " Style: passport standard compliance. "
            "Expression: neutral (no smile), mouth closed, eyes fully visible and open, hair not obscuring eyes, ears visible. "
            "Accessories: remove glasses, hats, and distracting jewelry; no reflections or shadows. Avoid uniforms; everyday clothing only. "
            "Background: plain pure white (#FFFFFF), evenly lit with no shadows. "
            "Composition: head centered, full face visible; avoid cropping chin/forehead; ensure even exposure and true-to-life color. "
            "Aspect: portrait orientation around 3:4. No artistic effects, filters, text, logos, borders, or color casts."
        )
        gp = (options or {}).get("gender_presentation") if isinstance(options, dict) else None
        if isinstance(gp, str) and gp.lower() in {"male","female","neutral"}:
            extra += f" Subject gender presentation is {gp.lower()}; do not change it."
        region = (options or {}).get("region") if isinstance(options, dict) else None
        if isinstance(region, str):
            r = region.upper()
            if r == "US":
                extra += " US-specific: plain white background; recent photo; no uniform; no headphones; no smiling; head size within acceptable range."
            elif r == "UK":
                extra += " UK-specific: light-coloured plain background; eyes fully visible; mouth closed; no glasses unless necessary; no shadows."
            elif r == "KR":
                extra += " KR-specific: clean white background; neutral expression; no accessories; natural skin tone."
    elif theme == "memory":
        extra = (
            " Style: heritage studio portrait with emotional warmth. "
            "Background: tasteful painterly studio backdrop (muted warm or sepia tones) replacing cluttered backgrounds. "
            "Lighting: soft key with gentle falloff; classic portrait contrast; subtle vignette to draw attention to the face. "
            "Treatment: archival film grade with very light grain and gentle halation; natural skin texture preserved; minimal retouch. "
            "Include a dignified, timeless mood; avoid novelty effects or cartoon stylization."
        )
    elif theme == "model":
        extra = (
            " Create a full-body professional model photoshoot portrait of the SAME person from the provided photo. "
            f" {_model_scenario()} "
            " Preserve facial identity and natural skin texture. Body proportions must be realistic and consistent with the subject. "
            " High-end fashion/editorial quality lighting and color. "
            " Composition: full-body or three-quarter view; allow dynamic angles and poses; include appropriate environment or studio set. "
            " Do not use plain passport-style white background unless the scenario implies a seamless set."
        )
        gp = (options or {}).get("gender_presentation") if isinstance(options, dict) else None
        if isinstance(gp, str) and gp.lower() in {"male","female","neutral"}:
            extra += f" Wardrobe should suit a {gp.lower()} presentation."
    elif theme == "fantasy_real":
        extra = (
            " Create a cinematic fantasy character PORTRAIT of the SAME person from the provided photo, in a photorealistic style. "
            f" {_fantasy_scenario()} "
            " Wardrobe and environment may change to match the theme, but identity, facial structure, and skin tone must be preserved. "
            " Photographic realism, natural skin texture, high dynamic range, no text or logos."
        )
    elif theme == "fantasy_anime":
        extra = (
            " Create an anime-style fantasy character portrait of the SAME person from the provided photo. "
            f" {_fantasy_scenario()} "
            " Stylization: anime/manga illustration with clean linework and subtle shading, expressive eyes. "
            " Keep key identity cues (hair style/color, facial proportions) consistent. No text or logos."
        )
    elif theme == "kpop":
        extra = (
            " Create a photorealistic K-pop idol style portrait of the SAME person from the provided photo. "
            f" {_kpop_scenario()} "
            " Skin finish: glossy yet natural (no plastic smoothing). Hair neatly styled. "
            " Preserve identity and proportions. No text/logos."
        )
        gp = (options or {}).get("gender_presentation") if isinstance(options, dict) else None
        if isinstance(gp, str) and gp.lower() in {"male","female","neutral"}:
            extra += f" Styling should suit a {gp.lower()} presentation."
    elif theme == "actor":
        extra = (
            " Create a photorealistic actor portrait/photoshoot of the SAME person from the provided photo. "
            f" {_actor_scenario()} "
            " Express professionalism and cinematic presence. Preserve identity and realism. No text/logos."
        )
    elif theme == "travel":
        extra = (
            " Create a photorealistic travel portrait of the SAME person from the provided photo, in a real-world location. "
            f" {(_travel_scenario() if not options or not options.get('location') else 'Location: ' + str(options['location']) + '. Outfit: neat travel attire. Lighting: natural for time of day.')} "
            " Composition: full-body or three-quarter view with clear environmental context; avoid plain studio backgrounds. "
            " Natural colors and realistic lighting."
        )
    elif theme == "anime":
        extra = (
            " Create an anime-style portrait of the SAME person from the provided photo. "
            f" Style: {((options.get('style') if options and options.get('style') else _anime_style()))}. "
            " Keep recognizable features (face shape, hairstyle/color cues). Clean linework, coherent anatomy. No text/logos."
        )
    elif theme == "activity":
        extra = (
            " Create a photorealistic ACTION photograph of the SAME person from the provided photo. "
            f" {(_activity_scenario() if not options or not options.get('category') else 'Activity category: ' + str(options['category']) + ' (use an appropriate realistic scene and safety gear).')} "
            " Composition: full-body or dynamic three-quarter; capture motion (e.g., panning blur background with sharp subject, or high-speed freeze of droplets). "
            f" Motion style: {((options.get('motion') if options and options.get('motion') in ['panning','freeze'] else 'auto'))}. "
            " Camera perspective may be low/high angle; allow Dutch tilt for drama. Include real environment relevant to the activity; do NOT use plain studio or passport-style backgrounds. "
            " Ensure realistic posture and visible safety gear when applicable (helmets, harness, life vest). "
            " Lighting and color should match the scene (outdoor daylight, indoor neon, etc.)."
        )
    elif theme == "profession":
        extra = (
            " Create a photorealistic professional portrait of the SAME person from the provided photo, representing a real-world occupation. "
            f" {(_profession_scenario() if not options or not options.get('role_keyword') else 'Profession: ' + str(options['role_keyword']) + '. Wardrobe and environment appropriate to the role.' )} "
            " Preserve identity and natural skin texture. No weapons, no brand logos, no text."
        )
    elif theme == "wedding":
        extra = (
            " Create a photorealistic wedding-style portrait of the SAME person from the provided photo. "
            f" {_wedding_scenario()} "
            " Elegant mood, tasteful color grading, realistic attire textures."
        )
        gp = (options or {}).get("gender_presentation") if isinstance(options, dict) else None
        if isinstance(gp, str):
            gl = gp.lower()
            if gl == "male":
                extra += " Use MALE formal attire (suit or tuxedo). Do NOT switch to wedding dress."
            elif gl == "female":
                extra += " Use FEMALE bridal attire (wedding dress or gown). Do NOT switch to tuxedo."
            elif gl == "neutral":
                extra += " Use androgynous formal styling (neutral suit/dress mix), keep presentation neutral."
    elif theme == "graduation":
        extra = (
            " Create a photorealistic graduation portrait of the SAME person from the provided photo. "
            f" {_graduation_scenario()} "
            " Keep facial identity and dignified tone."
        )
    elif theme == "traditional":
        extra = (
            " Create a photorealistic traditional studio portrait (Hanbok-inspired) of the SAME person from the provided photo. "
            f" {_traditional_scenario()} "
            " Painterly backdrop, warm tones, natural textures."
        )
        gp = (options or {}).get("gender_presentation") if isinstance(options, dict) else None
        if isinstance(gp, str):
            gl = gp.lower()
            if gl == "male":
                extra += " Use MALE hanbok variant (jeogori + baji + durumagi); do NOT switch to female dress."
            elif gl == "female":
                extra += " Use FEMALE hanbok variant (jeogori + chima/skirt); do NOT switch to male attire."
            elif gl == "neutral":
                extra += " Use a gender‑neutral hanbok styling with modest lines; keep presentation neutral."
    elif theme == "retro":
        extra = (
            " Create a photorealistic retro-era portrait of the SAME person from the provided photo. "
            f" {_retro_scenario()} "
            " Maintain realism without adding text or logos."
        )
    elif theme == "sports":
        extra = (
            " Create a photorealistic sports portrait of the SAME person from the provided photo. "
            f" {_sports_scenario()} "
            " Allow dynamic pose and motion feel while preserving identity."
        )
    elif theme == "musician":
        extra = (
            " Create a photorealistic musician/album-style portrait of the SAME person from the provided photo. "
            f" {_musician_scenario()} "
            " No text or titles; focus on lighting and mood."
        )
    elif theme == "film":
        extra = (
            " Create a photorealistic film-genre still of the SAME person from the provided photo. "
            f" {_film_scenario()} "
            " Cinematic composition and lighting; keep realism."
        )
    elif theme == "lookbook":
        extra = (
            " Create a photorealistic seasonal lookbook full-body portrait of the SAME person from the provided photo. "
            f" {_lookbook_scenario()} "
            " Fashion catalog quality, clean background or urban scene."
        )
        gp = (options or {}).get("gender_presentation") if isinstance(options, dict) else None
        if isinstance(gp, str) and gp.lower() in {"male","female","neutral"}:
            extra += f" Styling should suit a {gp.lower()} presentation."
    elif theme == "makeover":
        extra = (
            " Create a photorealistic headshot makeover of the SAME person from the provided photo. "
            f" Style: {_makeover_style()}. "
            " Maintain natural skin texture; tasteful grooming and polish."
        )
    elif theme == "meme":
        extra = (
            " Create a photorealistic surreal meme-style portrait of the SAME person from the provided photo, mixing many playful elements together at once. "
            f" {_meme_scenario()} "
            " Ensure everything is safe and harmless; do NOT depict injury or dangerous behavior. "
            " No text, no brand logos, no watermarks. Preserve identity and realistic human anatomy."
        )
    elif theme == "animal":
        extra = (
            " Create a photorealistic animal-inspired portrait of the SAME person from the provided photo. "
            f" {_animal_scenario()} "
            " Use realistic styling/costume/makeup cues (ears/headpiece, pattern hints) rather than cartoon morphing; preserve human anatomy and identity."
        )
    elif theme == "lifestage":
        extra = (
            " Create a photorealistic lifestage transformation portrait of the SAME person from the provided photo. "
            f" {_lifestage_scenario()} "
            " Wholesome, respectful depiction; no text/logos."
        )
    elif theme == "timetravel":
        extra = (
            " Create a photorealistic time-travel portrait of the SAME person from the provided photo. "
            f" {_timetravel_scenario()} "
            " Realistic attire and environment consistent with the era; preserve identity; no text/logos."
        )
    elif theme == "cosmos":
        extra = (
            " Create a photorealistic space travel portrait/composite of the SAME person from the provided photo. "
            f" {_cosmos_scenario()} "
            " Cinematic realism; safe depiction; no text/logos."
        )
    elif theme == "aerial_set":
        extra = (
            " Create a photorealistic third‑person aerial view of the SAME person from the provided photo, as if on a movie set being filmed. "
            f" {_aerial_set_scenario()} "
            " Show the subject within the wider scene; preserve identity; include crew/equipment naturally; no text/logos."
        )
    elif theme == "baby_studio":
        extra = (
            " Create a wholesome, photorealistic baby portrait studio scene using the provided photo. "
            f" {_baby_studio_scenario()} "
            " Gentle colors and lighting; preserve identity; no text/logos; tasteful and safe depiction."
        )
    else:
        extra = ""

    return common + extra + (_composition_text(comp_key) if comp_key else "")


def normalize_mime(mime_type: Optional[str]) -> str:
    if mime_type in {"image/png", "image/jpeg", "image/jpg"}:
        return "image/jpeg" if mime_type in {"image/jpeg", "image/jpg"} else "image/png"
    # Try to infer
    return "image/png"


app = FastAPI(title="AI Portrait Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # use wildcard CORS header reliably
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/generate")
def generate(body: GenerateBody, request: Request):
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set in environment for process PID=%s", os.getpid())
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")

    # Decode input to validate and possibly re-encode as PNG
    def decode_image_b64(b64: str) -> bytes:
        try:
            data = b64
            if isinstance(data, str) and data.startswith("data:"):
                # Accept data URL format: data:<mime>;base64,<payload>
                parts = data.split(",", 1)
                data = parts[1] if len(parts) == 2 else data
            return base64.b64decode(data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image base64. Expect raw base64 (or data URL) of PNG/JPEG.")

    input_bytes = decode_image_b64(body.image)
    if not input_bytes:
        logger.warning("/api/generate empty image payload from %s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=400, detail="Empty image payload")

    # Normalize mime type
    mime_type = normalize_mime(body.mime_type)
    logger.info("/api/generate theme=%s mime=%s img_len=%s", body.theme, mime_type, len(input_bytes))

    # Pre-compress large inputs to avoid upstream 400 due to payload limits
    def preprocess_input(img_bytes: bytes, mime: str) -> (bytes, str):
        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            w, h = img.size
            max_side = 1600
            if max(w, h) > max_side:
                scale = max_side / float(max(w, h))
                nw, nh = int(w * scale), int(h * scale)
                img = img.resize((nw, nh), Image.LANCZOS)
            buf = BytesIO()
            # Prefer JPEG to reduce payload size
            img.save(buf, format="JPEG", quality=90)
            out = buf.getvalue()
            return out, "image/jpeg"
        except Exception as e:
            logger.warning("preprocess_input failed: %s", e)
            return img_bytes, mime

    # If input is large (>8MB) or mime unknown, compress
    if len(input_bytes) > 8 * 1024 * 1024 or mime_type not in {"image/png", "image/jpeg"}:
        before = len(input_bytes)
        input_bytes, mime_type = preprocess_input(input_bytes, mime_type)
        logger.info("compressed input %s -> %s bytes, mime=%s", before, len(input_bytes), mime_type)

    # Choose composition (random for non-regulated themes) and build prompt
    comp_key = _choose_composition_for_theme(body.theme, body.options)
    # For ID photos, force half-body framing so shoulders/chest are visible
    if body.theme in {"passport", "resume"}:
        comp_key = "half"
    prompt = build_prompt(body.theme, comp_key, body.options)
    logger.info("composition=%s", comp_key)

    # Construct contents for Gemini, with optional identity face crop to improve consistency
    def make_identity_crop(img_bytes: bytes):
        if not CV2_AVAILABLE:
            return None
        try:
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            cvimg = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if cvimg is None:
                return None
            gray = cv2.cvtColor(cvimg, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(48,48))
            if len(faces) == 0:
                return None
            x,y,w,h = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
            pad = int(max(w,h)*0.45)
            x0 = max(0, x-pad); y0 = max(0, y-pad)
            x1 = min(cvimg.shape[1], x+w+pad); y1 = min(cvimg.shape[0], y+h+pad)
            crop = cvimg[y0:y1, x0:x1]
            # Resize to manageable ref size
            ref_w = 512
            ch, cw = crop.shape[:2]
            if cw > ref_w:
                scale = ref_w/float(cw)
                crop = cv2.resize(crop, (ref_w, int(ch*scale)), interpolation=cv2.INTER_LANCZOS4)
            _, enc = cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            return enc.tobytes(), 'image/jpeg'
        except Exception:
            return None

    identity_part = None
    id_crop = make_identity_crop(input_bytes)
    if id_crop is not None:
        cid_bytes, cid_mime = id_crop
        identity_part = {"inlineData": {"mimeType": cid_mime, "data": base64.b64encode(cid_bytes).decode("utf-8")}}

    parts = [{"text": prompt}, {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(input_bytes).decode("utf-8")}}]
    if identity_part:
        parts = [{"text": "Identity reference close-up (keep same person):"}, identity_part] + parts

    contents = [{"role": "user", "parts": parts}]

    def model_generate(image_bytes: bytes, prompt_override: Optional[str] = None, temperature: float = 1.05) -> str:
        payload_full = {
            "systemInstruction": {
                "role": "system",
                "parts": [
                    {"text": (
                        "Follow professional studio portrait standards. Preserve identity. Do not change gender or gender expression, skin tone, ethnicity, age, or body type unless the user explicitly requests it. "
                        "Natural skin texture, clean background, photographic realism. Absolutely no text/letters/numbers/logos/watermarks anywhere in the image."
                    )}
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": (prompt_override or prompt)},
                        {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(image_bytes).decode("utf-8")}},
                    ],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.9,
                "topK": 40
            },
        }
        payload_min = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": (prompt_override or prompt)},
                        {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(image_bytes).decode("utf-8")}},
                    ],
                }
            ]
        }

        def call(payload):
            try:
                return requests.post(
                    GEMINI_ENDPOINT,
                    headers={
                        "Content-Type": "application/json",
                        "X-goog-api-key": GEMINI_API_KEY,
                    },
                    json=payload,
                    timeout=60,
                )
            except requests.RequestException as e:
                logger.exception("Upstream request error: %s", e)
                raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

        resp = call(payload_full)
        if resp.status_code == 400:
            # Retry without systemInstruction/generationConfig (some models are strict)
            try:
                snippet = resp.text[:300]
                logger.warning("400 INVALID_ARGUMENT with full payload, retrying minimal. body=%s", snippet)
            except Exception:
                pass
            resp = call(payload_min)

        if resp.status_code != 200:
            snippet = resp.text[:400] if hasattr(resp, 'text') else str(resp.status_code)
            logger.error("Upstream non-200 status=%s body=%s", resp.status_code, snippet)
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        data = resp.json()
        inline_b64: Optional[str] = None
        try:
            candidates = data.get("candidates", [])
            for cand in candidates:
                parts = cand.get("content", {}).get("parts", [])
                for p in parts:
                    if "inlineData" in p:
                        inline_b64 = p["inlineData"]["data"]
                        break
                if inline_b64:
                    break
        except Exception as e:
            logger.exception("Failed to parse upstream response: %s", e)
            inline_b64 = None
        if not inline_b64:
            logger.error("No image returned from model for theme=%s", body.theme)
            raise HTTPException(status_code=500, detail="No image returned from model")
        return inline_b64

    # Multi-subject support: detect multiple faces and generate for each crop
    def detect_faces(image_bytes: bytes):
        if not CV2_AVAILABLE:
            return []
        try:
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img_cv = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img_cv is None:
                return []
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48,48))
            faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
            return faces
        except Exception:
            return []

    faces = detect_faces(input_bytes)
    multiple = len(faces) >= 2

    # Process output image to target aspect/size per theme and composition
    def get_target_size(theme: str, comp: Optional[str]):
        if theme == "passport":
            return (900, 1200)  # 3:4 regulated
        if theme == "resume":
            return (900, 1200)  # 3:4 common ID/resume portrait aspect
        # Composition-driven sizes
        if comp == "full" or comp == "three_quarter":
            return (1080, 1620)  # 2:3 tall
        if comp == "half":
            return (1024, 1280)  # 4:5
        if comp == "close":
            return (900, 1200)   # 3:4 tight portrait
        # Fallback by theme
        if theme in {"model", "kpop", "actor", "travel", "activity", "profession", "aerial_set"}:
            return (1080, 1620)
        return (1024, 1280)

    def resize_cover(img: Image.Image, tw: int, th: int) -> Image.Image:
        w, h = img.size
        if w == 0 or h == 0:
            return img
        scale = max(tw / w, th / h)
        nw, nh = int(w * scale), int(h * scale)
        img2 = img.resize((nw, nh), Image.LANCZOS)
        left = max(0, (nw - tw) // 2)
        top = max(0, (nh - th) // 2)
        box = (left, top, left + tw, top + th)
        img3 = img2.crop(box)
        return img3

    # Helper to process a single generated base64 image
    def process_and_save(inline_b64: str, comp_key_local: Optional[str], theme: str):
        # Decode model image, apply processing
        out_img: Image.Image
        try:
            out_bytes_local = base64.b64decode(inline_b64)
            out_img = Image.open(BytesIO(out_bytes_local))
            out_img.load()
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to decode model image")

        def enforce_id_crop(pil_img: Image.Image, target_w: int, target_h: int, head_ratio: float = 0.65, eye_line_from_top: float = 0.43) -> Image.Image:
            if not CV2_AVAILABLE:
                # Fallback without OpenCV: simple cover crop
                return resize_cover(pil_img.convert("RGBA"), target_w, target_h)
            # Convert PIL -> CV2
            img = np.array(pil_img.convert("RGB"))
            img_cv = img[:, :, ::-1]
            h0, w0 = img_cv.shape[:2]
            # Detect face (largest)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            faces_loc = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(int(min(w0, h0)*0.15), int(min(w0, h0)*0.15)))
            if len(faces_loc) == 0:
                # fallback: simple cover center crop
                return resize_cover(pil_img.convert("RGBA"), target_w, target_h)
            # pick largest
            x, y, w, h = sorted(faces_loc, key=lambda f: f[2]*f[3], reverse=True)[0]
            # Desired head height in final
            desired_head_h = head_ratio * target_h
            scale = desired_head_h / max(h, 1)
            # Resize original by scale
            new_w, new_h = int(w0 * scale), int(h0 * scale)
            img_scaled = cv2.resize(img_cv, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            # Face center in scaled image
            cx = int((x + w/2) * scale)
            # Approximate eye line ~ 0.38 of face height from top
            eyes_y_scaled = int((y + 0.38*h) * scale)
            # Compute crop top-left so that eye line sits at specified position
            crop_x = cx - target_w // 2
            crop_y = int(eyes_y_scaled - 0.43 * target_h)
            # Clamp
            crop_x = max(0, min(crop_x, new_w - target_w))
            crop_y = max(0, min(crop_y, new_h - target_h))
            # If scaled image smaller than target, pad
            if new_w < target_w or new_h < target_h:
                pad_w = max(0, target_w - new_w)
                pad_h = max(0, target_h - new_h)
                img_scaled = cv2.copyMakeBorder(img_scaled, pad_h//2, pad_h - pad_h//2, pad_w//2, pad_w - pad_w//2, cv2.BORDER_REPLICATE)
                new_h, new_w = img_scaled.shape[:2]
                crop_x = max(0, min(crop_x, new_w - target_w))
                crop_y = max(0, min(crop_y, new_h - target_h))
            crop = img_scaled[crop_y:crop_y+target_h, crop_x:crop_x+target_w]
            if crop.shape[0] != target_h or crop.shape[1] != target_w:
                crop = cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
            pil_out = Image.fromarray(crop[:, :, ::-1])
            return pil_out

        try:
            tw, th = get_target_size(theme, comp_key_local)
            if theme in {"passport", "resume"}:
                # Make head smaller in the frame to include shoulders/chest
                # Passport: tighter but still chest-up; Resume: slightly looser
                out_img = enforce_id_crop(
                    out_img,
                    tw,
                    th,
                    head_ratio=0.45 if theme == "passport" else 0.50,
                    eye_line_from_top=0.43,
                )
            else:
                out_img = resize_cover(out_img.convert("RGBA"), tw, th)
        except Exception:
            pass

        # Re-encode processed image to PNG base64 and save
        buf = BytesIO()
        out_img.save(buf, format="PNG")
        processed_bytes_local = buf.getvalue()
        processed_b64_local = base64.b64encode(processed_bytes_local).decode("utf-8")

        out_dir = os.path.join(os.path.dirname(__file__), "static", "outputs")
        os.makedirs(out_dir, exist_ok=True)
        out_id_local = f"{uuid.uuid4().hex}.png"
        out_path_local = os.path.join(out_dir, out_id_local)
        with open(out_path_local, "wb") as f:
            f.write(processed_bytes_local)
        saved_url_local = f"/outputs/{out_id_local}"
        return processed_b64_local, saved_url_local

    # If multiple faces detected, crop around each face and call the model per face
    if multiple:
        # decode original for cropping
        arr = np.frombuffer(input_bytes, dtype=np.uint8) if CV2_AVAILABLE else None
        img_cv_src = cv2.imdecode(arr, cv2.IMREAD_COLOR) if CV2_AVAILABLE and arr is not None else None
        h0, w0 = (img_cv_src.shape[0], img_cv_src.shape[1]) if img_cv_src is not None else (0,0)
        results = []
        max_subjects = min(len(faces), 3)  # practical cap
        for idx, (x,y,w,h) in enumerate(faces[:max_subjects]):
            if img_cv_src is None:
                break
            # expand box to include shoulders
            cx, cy = x + w/2, y + h/2
            box_w = int(w * 2.0)
            box_h = int(h * 2.4)
            x0 = max(0, int(cx - box_w/2))
            y0 = max(0, int(cy - box_h*0.45))
            x1 = min(w0, x0 + box_w)
            y1 = min(h0, y0 + box_h)
            crop_cv = img_cv_src[y0:y1, x0:x1]
            _, enc = cv2.imencode('.png', crop_cv)
            # Encourage per-subject diversity
            variation_tag = uuid.uuid4().hex[:8]
            prompt_var = prompt + f"\nVariation tag: {variation_tag}. Produce a distinct, non-identical rendering."
            inline_b64 = model_generate(enc.tobytes(), prompt_override=prompt_var, temperature=1.1)
            processed_b64, saved_url = process_and_save(inline_b64, comp_key, body.theme)
            results.append({
                "subject_index": idx,
                "image_base64": processed_b64,
                "mime_type": "image/png",
                "saved_url": saved_url,
            })
        if results:
            # backward-compatible fields point to first result
            first = results[0]
            return {
                "images": results,
                "image_base64": first["image_base64"],
                "mime_type": "image/png",
                "saved_url": first["saved_url"],
            }

    # Single-subject path: generate multiple variants (default 3)
    # Determine shot count (per-request override via options, fallback to env)
    req_shots = SHOT_COUNT
    try:
        if isinstance(body.options, dict) and body.options.get("shots") is not None:
            req_shots = int(body.options.get("shots"))
    except Exception:
        req_shots = SHOT_COUNT
    req_shots = max(1, min(3, req_shots))

    # Generate unique variants (dedupe by hash)
    import hashlib
    variants = []
    seen = set()
    attempts = 0
    max_attempts = req_shots * 4
    while len(variants) < req_shots and attempts < max_attempts:
        attempts += 1
        variation_tag = uuid.uuid4().hex[:8]
        prompt_var = prompt + f"\nVariation tag: {variation_tag}. Produce a distinct, non-identical rendering."
        inline_b64 = model_generate(input_bytes, prompt_override=prompt_var, temperature=1.1)
        processed_b64, saved_url = process_and_save(inline_b64, comp_key, body.theme)
        try:
            img_bytes = base64.b64decode(processed_b64)
            h = hashlib.sha256(img_bytes).hexdigest()
        except Exception:
            h = uuid.uuid4().hex
        if h in seen:
            logger.info("duplicate variant detected, retrying (tag=%s)", variation_tag)
            continue
        seen.add(h)
        variants.append({
            "image_base64": processed_b64,
            "mime_type": "image/png",
            "saved_url": saved_url,
        })

    first = variants[0]
    return {
        "images": variants,
        "image_base64": first["image_base64"],
        "mime_type": first["mime_type"],
        "saved_url": first["saved_url"],
    }

    def enforce_id_crop(pil_img: Image.Image, target_w: int, target_h: int, head_ratio: float = 0.65, eye_line_from_top: float = 0.43) -> Image.Image:
        if not CV2_AVAILABLE:
            # Fallback without OpenCV: simple cover crop
            return resize_cover(pil_img.convert("RGBA"), target_w, target_h)
        # Convert PIL -> CV2
        img = np.array(pil_img.convert("RGB"))
        img_cv = img[:, :, ::-1]
        h0, w0 = img_cv.shape[:2]
        # Detect face (largest)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(int(min(w0, h0)*0.15), int(min(w0, h0)*0.15)))
        if len(faces) == 0:
            # fallback: simple cover center crop
            return resize_cover(pil_img.convert("RGBA"), target_w, target_h)
        # pick largest
        x, y, w, h = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
        # Desired head height in final
        desired_head_h = head_ratio * target_h
        scale = desired_head_h / max(h, 1)
        # Resize original by scale
        new_w, new_h = int(w0 * scale), int(h0 * scale)
        img_scaled = cv2.resize(img_cv, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        # Face center in scaled image
        cx = int((x + w/2) * scale)
        cy = int((y + h/2) * scale)
        # Approximate eye line ~ 0.38 of face height from top
        eyes_y_scaled = int((y + 0.38*h) * scale)
        # Compute crop top-left so that eye line sits at specified position
        crop_x = cx - target_w // 2
        crop_y = int(eyes_y_scaled - eye_line_from_top * target_h)
        # Clamp
        crop_x = max(0, min(crop_x, new_w - target_w))
        crop_y = max(0, min(crop_y, new_h - target_h))
        # If scaled image smaller than target, pad
        if new_w < target_w or new_h < target_h:
            pad_w = max(0, target_w - new_w)
            pad_h = max(0, target_h - new_h)
            img_scaled = cv2.copyMakeBorder(img_scaled, pad_h//2, pad_h - pad_h//2, pad_w//2, pad_w - pad_w//2, cv2.BORDER_REPLICATE)
            new_h, new_w = img_scaled.shape[:2]
            crop_x = max(0, min(crop_x, new_w - target_w))
            crop_y = max(0, min(crop_y, new_h - target_h))
        crop = img_scaled[crop_y:crop_y+target_h, crop_x:crop_x+target_w]
        if crop.shape[0] != target_h or crop.shape[1] != target_w:
            crop = cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        pil_out = Image.fromarray(crop[:, :, ::-1])
        return pil_out

    try:
        tw, th = get_target_size(body.theme, comp_key)
        if body.theme in {"passport", "resume"}:
            # Enforce regulated composition more strictly
            out_img = enforce_id_crop(out_img, tw, th, head_ratio=0.65 if body.theme=="passport" else 0.60, eye_line_from_top=0.43)
        else:
            out_img = resize_cover(out_img.convert("RGBA"), tw, th)
    except Exception:
        pass

    # Re-encode processed image to PNG base64
    buf = BytesIO()
    out_img.save(buf, format="PNG")
    processed_bytes = buf.getvalue()
    processed_b64 = base64.b64encode(processed_bytes).decode("utf-8")

    # Save output image into backend/static/outputs
    out_dir = os.path.join(os.path.dirname(__file__), "static", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_id = f"{uuid.uuid4().hex}.png"
    out_path = os.path.join(out_dir, out_id)

    with open(out_path, "wb") as f:
        f.write(processed_bytes)

    # Serve via static mount path
    saved_url = f"/outputs/{out_id}"
    return {"image_base64": processed_b64, "mime_type": "image/png", "saved_url": saved_url}


@app.post("/api/composite")
def composite(body: CompositeBody):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")

    # Decode inputs
    try:
        user_bytes = base64.b64decode(body.user_image)
        ref_bytes = base64.b64decode(body.ref_image)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 in inputs")

    # Basic file validations
    if len(user_bytes) == 0 or len(ref_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty image data")
    if len(user_bytes) > 12 * 1024 * 1024 or len(ref_bytes) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (max 12MB each)")

    user_mime = normalize_mime(body.user_mime_type)
    ref_mime = normalize_mime(body.ref_mime_type)
    if user_mime not in {"image/png", "image/jpeg"} or ref_mime not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=415, detail="Unsupported image mime type (use PNG or JPEG)")

    instruction = (
        "Create ONE photorealistic composite image. Use the REFERENCE image as the BASE SCENE. Replace/merge the PRIMARY FACE in the reference with the face from the USER PORTRAIT. "
        "Keep the reference background, props, and scene intact. Align head pose, scale, gaze direction, and skin tone; match lighting and color. Blend seams (hairline, edges), cast realistic shadows/reflections. "
        "Output must contain a single subject (the user) in the reference scene — do NOT duplicate or show two versions. "
        "Preserve the user's identity and realistic anatomy. Absolutely remove/avoid any text, letters, numbers, logos, or watermarks. "
        "No unsafe content."
    )
    if body.hint:
        instruction += f" Hint: {body.hint}."

    # Optional: detect faces to help the model focus
    def detect_face_box(img_bytes: bytes):
        if not CV2_AVAILABLE:
            return None
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        cv = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if cv is None:
            return None
        gray = cv2.cvtColor(cv, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48,48))
        if len(faces) == 0:
            return None
        x,y,w,h = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
        return (x,y,w,h), cv

    ref_face, ref_cv = detect_face_box(ref_bytes)
    user_face, user_cv = detect_face_box(user_bytes)

    # Build contents with optional face crops and coordinates
    parts = [{"text": instruction}]
    if ref_face and ref_cv is not None:
        x,y,w,h = ref_face[0], ref_face[1], ref_face[2], ref_face[3]
        parts.append({"text": f"Reference base scene (primary face approx bbox: x={x}, y={y}, w={w}, h={h}):"})
    else:
        parts.append({"text": "Reference base scene:"})
    parts.append({"inlineData": {"mimeType": ref_mime, "data": base64.b64encode(ref_bytes).decode("utf-8")}})

    parts.append({"text": "User portrait (cast this person's FACE into the reference):"})
    parts.append({"inlineData": {"mimeType": user_mime, "data": base64.b64encode(user_bytes).decode("utf-8")}})

    # Provide a close crop of the user's face to strengthen identity match
    try:
        if user_face and user_cv is not None:
            ux,uy,uw,uh = user_face[0], user_face[1], user_face[2], user_face[3]
            # expand box for hairline/chin
            pad = int(max(uw, uh)*0.4)
            x0 = max(0, ux - pad)
            y0 = max(0, uy - pad)
            x1 = min(user_cv.shape[1], ux + uw + pad)
            y1 = min(user_cv.shape[0], uy + uh + pad)
            crop = user_cv[y0:y1, x0:x1]
            _, enc = cv2.imencode('.png', crop)
            parts.append({"text": "User face close-up (for identity and texture):"})
            parts.append({"inlineData": {"mimeType": "image/png", "data": base64.b64encode(enc.tobytes()).decode("utf-8")}})
    except Exception:
        pass

    contents = [{"role": "user", "parts": parts}]

    try:
        resp = requests.post(
            GEMINI_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": GEMINI_API_KEY,
            },
            json={
                "systemInstruction": {
                    "role": "system",
                    "parts": [
                        {"text": (
                            "Photorealistic composite. Preserve identity. Do not change gender/gender expression, skin tone, ethnicity, age, or body type. "
                            "Absolutely no text/letters/numbers/logos/watermarks anywhere in the image."
                        )}
                    ]
                },
                "contents": contents,
            },
            timeout=60,
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    inline_b64: Optional[str] = None
    try:
        for cand in data.get("candidates", []):
            for p in cand.get("content", {}).get("parts", []):
                if "inlineData" in p:
                    inline_b64 = p["inlineData"]["data"]
                    break
            if inline_b64:
                break
    except Exception as e:
        logger.exception("Failed to parse upstream response: %s", e)
        inline_b64 = None
    if not inline_b64:
        logger.error("No image returned from model for theme=%s", body.theme)
        raise HTTPException(status_code=500, detail="No image returned from model")

    # Post-process to a consistent size (portrait)
    def resize_cover(img: Image.Image, tw: int, th: int) -> Image.Image:
        w, h = img.size
        if w == 0 or h == 0:
            return img
        scale = max(tw / w, th / h)
        nw, nh = int(w * scale), int(h * scale)
        img2 = img.resize((nw, nh), Image.LANCZOS)
        left = max(0, (nw - tw) // 2)
        top = max(0, (nh - th) // 2)
        box = (left, top, left + tw, top + th)
        img3 = img2.crop(box)
        return img3

    try:
        out_bytes = base64.b64decode(inline_b64)
        out_img = Image.open(BytesIO(out_bytes))
        out_img.load()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decode model image")

    tw, th = (1024, 1280)
    try:
        out_img = resize_cover(out_img.convert("RGBA"), tw, th)
    except Exception:
        pass

    buf = BytesIO()
    out_img.save(buf, format="PNG")
    processed_bytes = buf.getvalue()
    processed_b64 = base64.b64encode(processed_bytes).decode("utf-8")

    out_dir = os.path.join(os.path.dirname(__file__), "static", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_id = f"{uuid.uuid4().hex}.png"
    out_path = os.path.join(out_dir, out_id)
    with open(out_path, "wb") as f:
        f.write(processed_bytes)

    saved_url = f"/outputs/{out_id}"
    return {"image_base64": processed_b64, "mime_type": "image/png", "saved_url": saved_url}


# Static files (outputs) via ASGI mount
from fastapi.staticfiles import StaticFiles  # noqa: E402

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(os.path.join(static_dir, "outputs"), exist_ok=True)
app.mount("/outputs", StaticFiles(directory=os.path.join(static_dir, "outputs")), name="outputs")
