"""A–O paraphrase / adversarial variants. ModelBacked path must generalize; RuleBased is the lexical baseline."""

from tests.acceptance.test_cases import (
    CASE_A_ARTICLE,
    CASE_A_OBS,
    CASE_B,
    CASE_C_ARTICLE,
    CASE_C_USER,
    CASE_D,
    CASE_E,
    CASE_F_BODY,
    CASE_I,
    CASE_J,
    CASE_K,
    CASE_L,
    CASE_M,
    CASE_N,
    CASE_O_NEWS,
    CASE_O_MODEL,
)

PARAPHRASES: dict[str, list[dict]] = {
    "A": [
        {
            "article": CASE_A_ARTICLE,
            "obs": CASE_A_OBS,
        },
        {
            "article": "A household folding robot was shown. The vendor asserts that low-level actuation remains smooth and uninterrupted throughout the fold.",
            "obs": "The arm advances in short bursts separated by visible dwell periods.",
        },
        {
            "article": "Marketing copy says the cloth-folding machine produces stable continuous locomotion of the end-effector.",
            "obs": "I watched the demo: move then rest then move, repeatedly, during folding.",
        },
        {
            "article": "The firm attributes 'unbroken fluid motion' to its low-level controller during garment folding.",
            "obs": "On the show floor the manipulator halted between micro-motions in a way you could see.",
        },
        {
            "article": "Embodied folding product: company claim of continuous movement from the low-level brain.",
            "obs": "Field note: visible halt intervals interleaved with advances.",
        },
    ],
    "B": [
        {"article": CASE_B, "obs": None},
        {
            "article": "WorldDreamer-Orbit is described as one shared world model steering many robotic bodies. OrbitBench is promised later; first in-orbit validation is not claimed as already done. They call it a revolutionary seamless leap.",
            "obs": None,
        },
        {
            "article": "A collective-intelligence stack: one world / one model / many bodies, reducing explicit communication. Benchmark release is planned.",
            "obs": None,
        },
        {
            "article": "SpaceClaw's swarm architecture uses a shared world model. In-orbit results are a future plan, not a current fact.",
            "obs": None,
        },
    ],
    "C": [
        {"article": CASE_C_ARTICLE, "obs": CASE_C_USER},
        {
            "article": "The founder insists a single unified policy maps sensory input directly to whole-body joint commands, eventually replacing hierarchical stacks.",
            "obs": "Routing every high-rate proprioceptive packet through one large model may blow the latency and energy budget.",
        },
        {
            "article": "Startup narrative: end-to-end motor control on a humanoid will make layered controllers obsolete.",
            "obs": "The fastest embodied loop may not tolerate a giant unified model.",
        },
        {
            "article": "Founder opinion: train one large model for all motor control; hierarchy is a dead end.",
            "obs": "Energy cost of a unified high-frequency controller remains an open measurement.",
        },
    ],
    "D": [
        {"article": CASE_D, "obs": None},
        {
            "article": "Holding a minority stake does not necessarily imply an executive or labor relationship.",
            "obs": None,
        },
        {
            "article": "A celebrity kept a small slice of a beverage company without becoming an operator or employee.",
            "obs": None,
        },
        {
            "article": "Ownership of brand equity stayed separate from day-to-day employment and contractual operating duties.",
            "obs": None,
        },
        {
            "article": "The case is about shares versus a job: owning part of a consumer brand did not create an employment relationship.",
            "obs": None,
        },
    ],
    "E": [
        {"article": CASE_E, "obs": None},
        {"article": "Another lab posted a slightly higher MMLU on a point-release. No architecture, no robotics.", "obs": None},
        {"article": "Minor version bump, leaderboard +0.3, nothing about motor intelligence.", "obs": None},
        {"article": "Generic foundation-model changelog with a small exam-score improvement.", "obs": None},
    ],
    "F": [
        {"article": CASE_F_BODY, "obs": None},
        {"article": "Acme Corp announces Model Z at a press event. The company said Model Z is available today.", "obs": None},
    ],
    "I": [
        {"article": CASE_I, "obs": None},
        {
            "article": "A careful arXiv control paper argues the opposite of 'large unified models may be unsuitable for the fastest embodied-control loop' and reports latency numbers.",
            "obs": None,
        },
        {
            "article": "New measurements claim large unified models are necessary for high-frequency embodied motor control.",
            "obs": None,
        },
        {
            "article": "The paper contradicts the active Belief that large unified models may be unsuitable for the fastest embodied-control loop, with an architecture study.",
            "obs": None,
        },
    ],
    "J": [
        {"article": CASE_J, "obs": None},
        {
            "article": "A foundational treatment of temporal motor intelligence and embodied control loops; mechanism, not a product launch.",
            "obs": None,
        },
        {"article": "Textbook-grade principles of high-frequency motor control architecture.", "obs": None},
    ],
    "K": [
        {"article": CASE_K, "obs": None},
        {
            "article": "A concurrent method nearly identical to the active camera-ready draft on latency × energy evaluation may invalidate novelty.",
            "obs": None,
        },
        {
            "article": "This submission overlaps the user's active paper on high-frequency embodied motor control evaluation.",
            "obs": None,
        },
    ],
    "L": [
        {"article": CASE_L, "obs": None},
        {
            "article": "Decentralized local intelligence for swarm robotics looks promising, but there is no paper release, no code, no replication, no benchmark update.",
            "obs": None,
        },
        {"article": "Interesting swarm method, evidence still too thin to treat as settled.", "obs": None},
    ],
    "M": [
        {"article": CASE_M, "obs": None},
        {
            "article": "The company says the robot generalizes zero-shot. Footage shows one successful trial. This probably means the system is robust.",
            "obs": None,
        },
        {
            "article": "Founder: zero-shot generalization. Observation: a single success in the video. Inference language: therefore it is robust.",
            "obs": None,
        },
        {
            "article": "Attributed claim of zero-shot skill; the clip succeeds once; commentary says this suggests robustness.",
            "obs": None,
        },
    ],
    "N": [
        {"article": CASE_N, "obs": None},
        {"article": "Reimagine delight with a revolutionary seamless lifestyle robot. No measurements.", "obs": None},
        {"article": "Game-changing household magic. No architecture, no papers, no research question.", "obs": None},
        {"article": "Unlock your best life with a delightful companion gadget. Pure adjectives. Reimagine delight.", "obs": None},
    ],
    "O_NEWS": [
        {"article": CASE_O_NEWS, "obs": None},
        {"article": "Company X launches robot Y today at a product event in Shenzhen.", "obs": None},
        {
            "article": "Today Company X launches robot Y at a product event in Shenzhen.",
            "obs": None,
        },
    ],
    "O_MODEL": [
        {"article": CASE_O_MODEL, "obs": None},
        {
            "article": "Repeated evidence suggests semantic task intelligence and temporal motor intelligence scale differently.",
            "obs": None,
        },
        {
            "article": "Sustained results point to separable scaling of semantic task skill versus temporal motor skill.",
            "obs": None,
        },
    ],
}
