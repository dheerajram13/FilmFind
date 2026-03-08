"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import apiClient from "@/lib/api-client";
import { getBackdropUrl, getPlaceholderImage, getPosterUrl } from "@/lib/image-utils";
import { Movie, SixtyContext, SixtyMood, SixtyyCraving } from "@/types/api";

type Screen = "q1" | "q2" | "q3" | "analysing" | "result";

type ModeOption = {
  key: string;
  icon: string;
  label: string;
  description: string;
  searchPrompt: string;
  why: string;
};

type StepId = "q1" | "q2" | "q3";

type SixtySecondModeProps = {
  open: boolean;
  onClose: () => void;
  onApplyQuery: (query: string) => void;
};

const PROGRESS_BY_SCREEN: Record<Screen, number> = {
  q1: 10,
  q2: 40,
  q3: 65,
  analysing: 85,
  result: 100,
};

const MOOD_OPTIONS: ModeOption[] = [
  {
    key: "drained",
    icon: "🪫",
    label: "Drained & tired",
    description: "I want something that doesn't ask too much of me",
    searchPrompt: "something immersive but not exhausting",
    why: "You said you're drained, so the pick avoids heavy cognitive load.",
  },
  {
    key: "charged",
    icon: "⚡",
    label: "Wired & restless",
    description: "I want something that matches my energy",
    searchPrompt: "high-intensity with momentum and tension",
    why: "You're wired and restless, so this match keeps your energy level up.",
  },
  {
    key: "sad",
    icon: "🌧",
    label: "Sad or emotional",
    description: "I want to feel something deeply",
    searchPrompt: "emotionally deep with strong character arcs",
    why: "You asked for emotional depth, so this one is built for payoff.",
  },
  {
    key: "happy",
    icon: "☀️",
    label: "Good mood",
    description: "I want something fun, light, or exciting",
    searchPrompt: "uplifting with confident pacing",
    why: "You're in a good mood, so the match protects that tone.",
  },
  {
    key: "bored",
    icon: "😶",
    label: "Bored & numb",
    description: "I need something that surprises me",
    searchPrompt: "fresh and surprising with strong hooks",
    why: "You wanted novelty, so this pick is selected for unpredictability.",
  },
  {
    key: "curious",
    icon: "🔍",
    label: "Curious & alert",
    description: "I want something that makes me think",
    searchPrompt: "smart and layered with thematic depth",
    why: "You asked for something thought-provoking, so complexity is prioritized.",
  },
];

const CONTEXT_OPTIONS: ModeOption[] = [
  {
    key: "solo-night",
    icon: "🌙",
    label: "Solo, late night",
    description: "Just me, open to anything dark",
    searchPrompt: "for solo night viewing with immersive atmosphere",
    why: "Solo late-night context allows a more focused and intense pick.",
  },
  {
    key: "solo-day",
    icon: "☁️",
    label: "Solo, lazy day",
    description: "Low commitment viewing",
    searchPrompt: "easy-to-enter but still high quality",
    why: "Lazy-day context favors immediate pull and lower friction.",
  },
  {
    key: "partner",
    icon: "🫶",
    label: "With a partner",
    description: "Works for two different tastes",
    searchPrompt: "that works for two different tastes",
    why: "Partner mode filters toward broader two-person compatibility.",
  },
  {
    key: "friends",
    icon: "🍻",
    label: "With friends",
    description: "Group vibe, all enjoy",
    searchPrompt: "with crowd-friendly pacing and shared payoff",
    why: "Group context pushes toward high consensus and shared energy.",
  },
  {
    key: "family",
    icon: "👨‍👩‍👧",
    label: "Family night",
    description: "Mixed ages, safe for all",
    searchPrompt: "safe for mixed ages but still engaging",
    why: "Family-night constraints remove dark mismatches by design.",
  },
  {
    key: "date",
    icon: "🕯",
    label: "Date night",
    description: "Atmospheric, talk-worthy",
    searchPrompt: "atmospheric and conversation-worthy",
    why: "Date-night context prefers atmosphere and post-watch conversation.",
  },
];

const CRAVING_OPTIONS: ModeOption[] = [
  {
    key: "mind-blown",
    icon: "🤯",
    label: "\"What just happened\"",
    description: "Twist, revelation. I want to sit in silence after.",
    searchPrompt: "mind-bending with a powerful final reveal",
    why: "You asked to be mind-blown, so this match optimizes for payoff.",
  },
  {
    key: "cry",
    icon: "😭",
    label: "A good cry",
    description: "Emotionally wrecked in the best possible way.",
    searchPrompt: "emotionally devastating but cathartic",
    why: "The target outcome is catharsis, so emotional intensity is weighted higher.",
  },
  {
    key: "pumped",
    icon: "🔥",
    label: "Pumped up",
    description: "Adrenaline, victory. I want to feel alive.",
    searchPrompt: "high-adrenaline and momentum-driven",
    why: "You wanted adrenaline, so pacing and intensity were prioritized.",
  },
  {
    key: "laugh",
    icon: "😂",
    label: "Laughed hard",
    description: "Genuinely funny. Not just background pleasant.",
    searchPrompt: "genuinely funny with sharp rhythm",
    why: "You asked for real laughs, so comedic hit-rate is heavily weighted.",
  },
  {
    key: "inspired",
    icon: "✨",
    label: "Inspired",
    description: "Left with a new perspective or motivation.",
    searchPrompt: "inspiring and perspective-shifting",
    why: "You asked for inspiration, so thematic uplift is central to the pick.",
  },
  {
    key: "cosy",
    icon: "🛋",
    label: "Warm & cosy",
    description: "Safe, comforting. I want to feel good inside.",
    searchPrompt: "comforting and warm with emotional safety",
    why: "You wanted comfort, so the match avoids sharp tonal shocks.",
  },
];

const ANALYSIS_STEPS = [
  { icon: "🧠", text: "Decoding your mood state" },
  { icon: "🎯", text: "Matching emotional context" },
  { icon: "⚡", text: "Scoring 50,000+ films" },
  { icon: "✨", text: "Locking in your pick" },
];

const FALLBACK_RESULT: Movie = {
  id: -1,
  tmdb_id: -1,
  media_type: "movie",
  title: "Whiplash",
  original_title: "Whiplash",
  overview:
    "A young drummer pushes himself to the breaking point under a ruthless instructor at one of the top music conservatories in the country.",
  release_date: "2014-10-10",
  poster_path: null,
  backdrop_path: null,
  genres: [
    { id: 1, name: "Drama" },
    { id: 2, name: "Music" },
    { id: 3, name: "Psychological" },
  ],
  vote_average: 8.5,
  vote_count: 0,
  popularity: 0,
  runtime: 107,
  original_language: "en",
  tagline: null,
  streaming_providers: null,
};

const CONTEXT_FALLBACK = CONTEXT_OPTIONS[0];
const CRAVING_FALLBACK = CRAVING_OPTIONS[0];
const MOOD_FALLBACK = MOOD_OPTIONS[1];

function optionFor(list: ModeOption[], key: string | null, fallback: ModeOption): ModeOption {
  if (!key) return fallback;
  return list.find((option) => option.key === key) ?? fallback;
}

function formatStepTitle(screen: Screen): string {
  if (screen === "q1") return "Question 1 of 3";
  if (screen === "q2") return "Question 2 of 3";
  if (screen === "q3") return "Question 3 of 3";
  return "";
}

function parseYear(value: string | null): string {
  if (!value) return "TBA";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "TBA";
  return String(date.getFullYear());
}

function runtimeLabel(runtime: number | null): string | null {
  if (!runtime || runtime <= 0) return null;
  return `${runtime} min`;
}

function genreEmoji(movie: Movie): string {
  const firstGenre = movie.genres[0]?.name.toLowerCase() ?? "";
  if (firstGenre.includes("drama")) return "🎭";
  if (firstGenre.includes("thriller")) return "🔍";
  if (firstGenre.includes("sci")) return "🛸";
  if (firstGenre.includes("horror")) return "🪦";
  if (firstGenre.includes("comedy")) return "😂";
  if (firstGenre.includes("animation")) return "🧠";
  return "🎬";
}

function normalizeProviderName(provider: string): string {
  const lower = provider.toLowerCase();
  if (lower.includes("prime")) return "Prime Video";
  if (lower.includes("hbo") || lower === "max") return "HBO Max";
  if (lower.includes("apple")) return "Apple TV+";
  if (lower.includes("netflix")) return "Netflix";
  if (lower.includes("hulu")) return "Hulu";
  return provider;
}

function collectProviderNames(value: unknown, sink: Set<string>) {
  if (!value) return;
  if (Array.isArray(value)) {
    value.forEach((entry) => collectProviderNames(entry, sink));
    return;
  }
  if (typeof value !== "object") return;
  const objectValue = value as Record<string, unknown>;
  const providerName = objectValue.provider_name;
  if (typeof providerName === "string" && providerName.length > 0) sink.add(providerName);
  Object.values(objectValue).forEach((entry) => collectProviderNames(entry, sink));
}

function primaryProvider(movie: Movie): string {
  if (!movie.streaming_providers || typeof movie.streaming_providers !== "object") return "Netflix";
  const names = new Set<string>();
  collectProviderNames(movie.streaming_providers, names);
  const first = Array.from(names)[0];
  return first ? normalizeProviderName(first) : "Netflix";
}

function formatContextLabel(key: string): string {
  return optionFor(CONTEXT_OPTIONS, key, CONTEXT_FALLBACK).label;
}

function formatCravingLabel(key: string): string {
  return optionFor(CRAVING_OPTIONS, key, CRAVING_FALLBACK).label.replace(/"/g, "");
}

// Map frontend option keys to backend enum values
const MOOD_KEY_MAP: Record<string, SixtyMood> = {
  happy: "happy",
  sad: "sad",
  charged: "charged",
  chill: "chill",
  adventurous: "adventurous",
  romantic: "romantic",
  // frontend-only keys → closest backend value
  drained: "chill",
  bored: "adventurous",
  curious: "charged",
};

const CONTEXT_KEY_MAP: Record<string, SixtyContext> = {
  "solo-night": "solo-night",
  "solo-day": "background",
  partner: "date-night",
  friends: "friends",
  family: "family",
  date: "date-night",
  "movie-night": "movie-night",
  background: "background",
};

const CRAVING_KEY_MAP: Record<string, SixtyyCraving> = {
  "mind-blown": "mind-blown",
  cry: "cry",
  pumped: "thrilled",
  laugh: "laugh",
  inspired: "inspired",
  cosy: "comforted",
  thrilled: "thrilled",
  scared: "scared",
  comforted: "comforted",
  wowed: "wowed",
};

function toBackendMood(key: string): SixtyMood {
  return MOOD_KEY_MAP[key] ?? "happy";
}
function toBackendContext(key: string): SixtyContext {
  return CONTEXT_KEY_MAP[key] ?? "solo-night";
}
function toBackendCraving(key: string): SixtyyCraving {
  return CRAVING_KEY_MAP[key] ?? "inspired";
}

function buildModeQuery(moodKey: string, contextKey: string, cravingKey: string): string {
  const mood = optionFor(MOOD_OPTIONS, moodKey, MOOD_FALLBACK);
  const context = optionFor(CONTEXT_OPTIONS, contextKey, CONTEXT_FALLBACK);
  const craving = optionFor(CRAVING_OPTIONS, cravingKey, CRAVING_FALLBACK);
  return `${mood.searchPrompt}, ${context.searchPrompt}, ${craving.searchPrompt}`;
}

type SixtyPickResult = { movie: Movie; matchScore: number; whyReasons: string[]; sessionId: string };

async function resolveMovieSixtyPick(
  moodKey: string,
  contextKey: string,
  cravingKey: string,
  sessionToken: string,
  secondsTaken: number,
): Promise<SixtyPickResult> {
  try {
    const response = await apiClient.sixtyPick({
      mood: toBackendMood(moodKey),
      context: toBackendContext(contextKey),
      craving: toBackendCraving(cravingKey),
      session_token: sessionToken,
      seconds_taken: secondsTaken,
    });
    return {
      movie: response.film,
      matchScore: response.match_score,
      whyReasons: response.why_reasons,
      sessionId: response.session_id,
    };
  } catch {
    // Fall back to text search if the endpoint fails
    const query = buildModeQuery(moodKey, contextKey, cravingKey);
    try {
      const searchResponse = await apiClient.search(query, undefined, 12);
      const film = searchResponse.results[0] as unknown as Movie | undefined;
      if (film) {
        const mood = optionFor(MOOD_OPTIONS, moodKey, MOOD_FALLBACK);
        const context = optionFor(CONTEXT_OPTIONS, contextKey, CONTEXT_FALLBACK);
        const craving = optionFor(CRAVING_OPTIONS, cravingKey, CRAVING_FALLBACK);
        return {
          movie: film,
          matchScore: 94,
          whyReasons: [mood.why, context.why, craving.why],
          sessionId: "",
        };
      }
    } catch {
      // ignore nested error
    }
    return {
      movie: FALLBACK_RESULT,
      matchScore: 94,
      whyReasons: [MOOD_FALLBACK.why, CONTEXT_FALLBACK.why, CRAVING_FALLBACK.why],
      sessionId: "",
    };
  }
}

export function SixtySecondMode({ open, onClose, onApplyQuery }: SixtySecondModeProps) {
  const [screen, setScreen] = useState<Screen>("q1");
  const [timerSeconds, setTimerSeconds] = useState(60);
  const [timerRunning, setTimerRunning] = useState(false);
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [selectedContext, setSelectedContext] = useState<string | null>(null);
  const [selectedCraving, setSelectedCraving] = useState<string | null>(null);
  const [analysisCountdown, setAnalysisCountdown] = useState(3);
  const [analysisVisibleSteps, setAnalysisVisibleSteps] = useState(0);
  const [resultMovie, setResultMovie] = useState<Movie | null>(null);
  const [resultMatch, setResultMatch] = useState(95);
  const [resultQuery, setResultQuery] = useState("");
  const [resultWhy, setResultWhy] = useState<string[]>([]);
  const [resultElapsed, setResultElapsed] = useState<number | null>(null);
  const [resultSessionId, setResultSessionId] = useState<string>("");
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

  const timeoutRef = useRef<number[]>([]);
  const intervalRef = useRef<number[]>([]);
  const runIdRef = useRef(0);

  const queueTimeout = useCallback((callback: () => void, delayMs: number) => {
    const id = window.setTimeout(callback, delayMs);
    timeoutRef.current.push(id);
  }, []);

  const clearScheduledWork = useCallback(() => {
    timeoutRef.current.forEach((id) => window.clearTimeout(id));
    intervalRef.current.forEach((id) => window.clearInterval(id));
    timeoutRef.current = [];
    intervalRef.current = [];
  }, []);

  const resetFlow = useCallback(() => {
    runIdRef.current += 1;
    clearScheduledWork();
    setScreen("q1");
    setTimerSeconds(60);
    setTimerRunning(true);
    setSelectedMood(null);
    setSelectedContext(null);
    setSelectedCraving(null);
    setAnalysisCountdown(3);
    setAnalysisVisibleSteps(0);
    setResultMovie(null);
    setResultMatch(95);
    setResultQuery("");
    setResultWhy([]);
    setResultElapsed(null);
    setResultSessionId("");
    setIsTransitioning(false);
    setShareOpen(false);
  }, [clearScheduledWork]);

  useEffect(() => {
    if (!open) {
      clearScheduledWork();
      return;
    }

    queueTimeout(() => resetFlow(), 0);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
      clearScheduledWork();
    };
  }, [clearScheduledWork, open, queueTimeout, resetFlow]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (shareOpen) {
        setShareOpen(false);
        return;
      }
      onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open, shareOpen]);

  useEffect(() => {
    if (!open || !timerRunning) return;
    const intervalId = window.setInterval(() => {
      setTimerSeconds((current) => Math.max(0, current - 1));
    }, 1000);
    intervalRef.current.push(intervalId);
    return () => window.clearInterval(intervalId);
  }, [open, timerRunning]);

  const progress = PROGRESS_BY_SCREEN[screen];
  const isQuestionScreen = screen === "q1" || screen === "q2" || screen === "q3";
  const stepTitle = formatStepTitle(screen);

  const footerLabel = useMemo(() => {
    if (screen === "result") {
      if (resultElapsed !== null) return `✦ Done in ${resultElapsed}s`;
      return "✦ Decided in under 60 seconds";
    }
    if (screen === "analysing") return "Finalising your pick";
    return `⏱ ${timerSeconds}s remaining`;
  }, [resultElapsed, screen, timerSeconds]);

  const activeMood = optionFor(MOOD_OPTIONS, selectedMood, MOOD_FALLBACK);
  const activeContext = optionFor(CONTEXT_OPTIONS, selectedContext, CONTEXT_FALLBACK);
  const activeCraving = optionFor(CRAVING_OPTIONS, selectedCraving, CRAVING_FALLBACK);

  const ringOffset = useMemo(() => {
    const circumference = 150.8;
    return circumference * (1 - analysisCountdown / 3);
  }, [analysisCountdown]);

  const resultPosterUrl = resultMovie
    ? getPosterUrl(resultMovie.poster_path, "w500") ||
      getBackdropUrl(resultMovie.backdrop_path, "w780") ||
      getPlaceholderImage()
    : getPlaceholderImage();

  const resolvedMovie: Movie = resultMovie ?? FALLBACK_RESULT;

  const runAnalysis = useCallback((moodKey: string, contextKey: string, cravingKey: string) => {
    const flowRunId = runIdRef.current + 1;
    runIdRef.current = flowRunId;

    setIsTransitioning(false);
    setShareOpen(false);
    setTimerRunning(false);
    setScreen("analysing");
    setAnalysisVisibleSteps(0);
    setAnalysisCountdown(3);

    const elapsed = Math.max(1, 60 - timerSeconds);
    const query = buildModeQuery(moodKey, contextKey, cravingKey);
    setResultQuery(query);

    const sessionToken = `ff-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const resultPromise = resolveMovieSixtyPick(moodKey, contextKey, cravingKey, sessionToken, elapsed);

    ANALYSIS_STEPS.forEach((_, index) => {
      queueTimeout(() => {
        if (runIdRef.current !== flowRunId) return;
        setAnalysisVisibleSteps(index + 1);
      }, index * 500);
    });

    queueTimeout(() => setAnalysisCountdown(2), 1000);
    queueTimeout(() => setAnalysisCountdown(1), 2000);
    queueTimeout(() => setAnalysisCountdown(0), 3000);

    queueTimeout(async () => {
      if (runIdRef.current !== flowRunId) return;
      const { movie, matchScore, whyReasons, sessionId } = await resultPromise;
      if (runIdRef.current !== flowRunId) return;

      setResultMovie(movie);
      setResultMatch(matchScore);
      setResultElapsed(elapsed);
      setResultWhy(whyReasons);
      setResultSessionId(sessionId);
      setScreen("result");
    }, 3000);
  }, [queueTimeout, timerSeconds]);

  const skipToResult = useCallback(() => {
    const moodKey = selectedMood ?? MOOD_FALLBACK.key;
    const contextKey = selectedContext ?? CONTEXT_FALLBACK.key;
    const cravingKey = selectedCraving ?? CRAVING_FALLBACK.key;
    setSelectedMood(moodKey);
    setSelectedContext(contextKey);
    setSelectedCraving(cravingKey);
    runAnalysis(moodKey, contextKey, cravingKey);
  }, [runAnalysis, selectedContext, selectedCraving, selectedMood]);

  useEffect(() => {
    if (!timerRunning || timerSeconds > 0) return;
    queueTimeout(() => skipToResult(), 0);
  }, [queueTimeout, skipToResult, timerRunning, timerSeconds]);

  const handleSelect = (step: StepId, key: string) => {
    if (isTransitioning) return;
    setIsTransitioning(true);

    if (step === "q1") {
      setSelectedMood(key);
      queueTimeout(() => {
        setScreen("q2");
        setIsTransitioning(false);
      }, 350);
      return;
    }

    if (step === "q2") {
      setSelectedContext(key);
      queueTimeout(() => {
        setScreen("q3");
        setIsTransitioning(false);
      }, 350);
      return;
    }

    setSelectedCraving(key);
    const moodKey = selectedMood ?? MOOD_FALLBACK.key;
    const contextKey = selectedContext ?? CONTEXT_FALLBACK.key;
    queueTimeout(() => runAnalysis(moodKey, contextKey, key), 350);
  };

  const resultMetaRuntime = runtimeLabel(resolvedMovie.runtime);
  const resultTags = resolvedMovie.genres.slice(0, 3).map((genre) => genre.name);
  const resultLanguage = resolvedMovie.original_language?.toUpperCase() || "N/A";
  const watchProvider = primaryProvider(resolvedMovie);
  const shareText = `FilmFind picked ${resolvedMovie.title} for me in under 60 seconds.`;

  const shareToX = () => {
    const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(
      `${shareText} ${resultWhy[0] ?? ""}`
    )}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const shareNative = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `FilmFind: ${resolvedMovie.title}`,
          text: `${shareText} ${resultWhy[0] ?? ""}`,
        });
        return;
      } catch {
        // User canceled share.
      }
    }
  };

  const copyShareLink = async () => {
    const slug = resolvedMovie.title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const link = `https://filmfind.app/pick/${slug}?ref=60sec`;
    await navigator.clipboard.writeText(link);
  };

  if (!open) return null;

  return (
    <div
      className="ff60-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="ff60-shell" onMouseDown={(event) => event.stopPropagation()}>
        <div className="ff60-progress">
          <div className="ff60-progress-fill" style={{ width: `${progress}%` }} />
        </div>

        <header className="ff60-nav">
          <button type="button" className="ff60-logo" onClick={resetFlow}>
            Film<span>Find</span>
          </button>
          <div className="ff60-mode">
            <span className="ff60-mode-dot" />
            60 Second Mode
          </div>
          <button type="button" className="ff60-close" onClick={onClose} aria-label="Close 60 second mode">
            ✕
          </button>
        </header>

        <div className="ff60-stage">
          {isQuestionScreen && (
            <div className="ff60-q-wrap">
              <div className="ff60-step">
                <span>{stepTitle}</span>
                <div className="ff60-step-dots">
                  <span className={`ff60-dot ${screen === "q1" ? "active" : "done"}`} />
                  <span className={`ff60-dot ${screen === "q2" ? "active" : screen === "q3" ? "done" : ""}`} />
                  <span className={`ff60-dot ${screen === "q3" ? "active" : ""}`} />
                </div>
              </div>

              {screen === "q1" && (
                <>
                  <h3 className="ff60-q-title">
                    HOW DO YOU
                    <br />
                    FEEL RIGHT NOW?
                  </h3>
                  <p className="ff60-q-sub">Not what you usually watch, what you need tonight.</p>
                  <div className="ff60-options cols2">
                    {MOOD_OPTIONS.map((option) => (
                      <button
                        key={option.key}
                        type="button"
                        className={`ff60-option ${selectedMood === option.key ? "selected" : ""}`}
                        onClick={() => handleSelect("q1", option.key)}
                      >
                        <span className="ff60-option-icon">{option.icon}</span>
                        <span className="ff60-option-label">{option.label}</span>
                        <span className="ff60-option-desc">{option.description}</span>
                      </button>
                    ))}
                  </div>
                </>
              )}

              {screen === "q2" && (
                <>
                  <h3 className="ff60-q-title">
                    WHAT&apos;S YOUR
                    <br />
                    SITUATION?
                  </h3>
                  <p className="ff60-q-sub">Who you&apos;re watching with changes everything.</p>
                  <div className="ff60-options cols3">
                    {CONTEXT_OPTIONS.map((option) => (
                      <button
                        key={option.key}
                        type="button"
                        className={`ff60-option ${selectedContext === option.key ? "selected" : ""}`}
                        onClick={() => handleSelect("q2", option.key)}
                      >
                        <span className="ff60-option-icon">{option.icon}</span>
                        <span className="ff60-option-label">{option.label}</span>
                        <span className="ff60-option-desc">{option.description}</span>
                      </button>
                    ))}
                  </div>
                </>
              )}

              {screen === "q3" && (
                <>
                  <h3 className="ff60-q-title">
                    WHAT DO YOU
                    <br />
                    WANT TO FEEL?
                  </h3>
                  <p className="ff60-q-sub">The feeling after the credits roll. Pick the one that calls to you.</p>
                  <div className="ff60-options cols2">
                    {CRAVING_OPTIONS.map((option) => (
                      <button
                        key={option.key}
                        type="button"
                        className={`ff60-option ${selectedCraving === option.key ? "selected" : ""}`}
                        onClick={() => handleSelect("q3", option.key)}
                      >
                        <span className="ff60-option-icon">{option.icon}</span>
                        <span className="ff60-option-label">{option.label}</span>
                        <span className="ff60-option-desc">{option.description}</span>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {screen === "analysing" && (
            <div className="ff60-analysing">
              <div className="ff60-ring-wrap">
                <svg viewBox="0 0 56 56" width="56" height="56">
                  <circle className="ff60-ring-bg" cx="28" cy="28" r="24" />
                  <circle
                    className="ff60-ring-fill"
                    cx="28"
                    cy="28"
                    r="24"
                    strokeDasharray="150.8"
                    strokeDashoffset={ringOffset}
                  />
                </svg>
                <span className="ff60-ring-num">{analysisCountdown}</span>
              </div>

              <h3 className="ff60-analysing-title">
                FINDING YOUR
                <br />
                <span>PERFECT MATCH.</span>
              </h3>

              <div className="ff60-analysis-steps">
                {ANALYSIS_STEPS.map((step, index) => {
                  const visible = analysisVisibleSteps > index;
                  const done = analysisVisibleSteps > index;
                  return (
                    <div key={step.text} className={`ff60-analysis-step ${visible ? "show" : ""} ${done ? "done" : ""}`}>
                      <span className="ff60-analysis-icon">{step.icon}</span>
                      <span>{step.text}</span>
                      <span className="ff60-analysis-check">✓</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {screen === "result" && (
            <div className="ff60-result-wrap">
              <div className="ff60-result-eyebrow">
                <span>✦</span> Your 60-second pick
              </div>
              <article className="ff60-result-card">
                <div className="ff60-result-poster">
                  <Image
                    src={resultPosterUrl}
                    alt={`${resolvedMovie.title} poster`}
                    fill
                    sizes="(max-width: 760px) 100vw, 720px"
                    className="ff60-result-poster-image"
                  />
                  <div className="ff60-poster-tint" />
                  <div className="ff60-poster-emoji">{genreEmoji(resolvedMovie)}</div>
                  <div className="ff60-result-score">{resultMatch}% match</div>
                </div>

                <div className="ff60-result-body">
                  <div className="ff60-result-tags">
                    {resultTags.map((tag) => (
                      <span key={tag} className="ff60-result-tag">
                        {tag}
                      </span>
                    ))}
                  </div>

                  <h3 className="ff60-result-title">{resolvedMovie.title.toUpperCase()}</h3>
                  <div className="ff60-result-meta">
                    <span className="rating">★ {(resolvedMovie.vote_average ?? 0).toFixed(1)}</span>
                    <span>{parseYear(resolvedMovie.release_date)}</span>
                    {resultMetaRuntime && <span>{resultMetaRuntime}</span>}
                    <span>{resultLanguage}</span>
                  </div>

                  <p className="ff60-result-synopsis">
                    {resolvedMovie.overview ||
                      "A high-confidence FilmFind pick based on your mood, context, and desired emotional outcome."}
                  </p>

                  <p className="ff60-why-label">Why FilmFind picked this for you tonight</p>
                  <div className="ff60-why-list">
                    {resultWhy.map((reason) => (
                      <div key={reason} className="ff60-why-pill">
                        <span className="ff60-why-dot" />
                        <span>{reason}</span>
                      </div>
                    ))}
                  </div>

                  <div className="ff60-result-actions">
                    <button type="button" className="ff60-btn-watch" onClick={() => {
                      if (resultSessionId) apiClient.sixtyAction(resultSessionId, { watch_clicked: true }).catch(() => {});
                      onApplyQuery(resultQuery);
                    }}>
                      ▶ Watch on {watchProvider}
                    </button>
                    <button type="button" className="ff60-btn-share" onClick={() => {
                      if (resultSessionId) apiClient.sixtyAction(resultSessionId, { share_clicked: true }).catch(() => {});
                      setShareOpen(true);
                    }}>
                      ↗ Share
                    </button>
                    <button type="button" className="ff60-btn-retry" onClick={() => {
                      if (resultSessionId) apiClient.sixtyAction(resultSessionId, { retry_clicked: true }).catch(() => {});
                      resetFlow();
                    }}>
                      Try again
                    </button>
                  </div>
                </div>
              </article>
            </div>
          )}
        </div>

        <footer className="ff60-footer">
          <span className={`ff60-footer-label ${timerRunning ? "active" : ""}`}>{footerLabel}</span>
          {isQuestionScreen && (
            <button type="button" className="ff60-skip" onClick={skipToResult}>
              Skip to result →
            </button>
          )}
        </footer>
      </section>

      {shareOpen && (
        <div
          className="ff60-share-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setShareOpen(false);
          }}
        >
          <div className="ff60-share-modal" onMouseDown={(event) => event.stopPropagation()}>
            <button type="button" className="ff60-share-close" onClick={() => setShareOpen(false)} aria-label="Close share">
              ✕
            </button>
            <h4 className="ff60-share-title">
              SHARE THIS
              <br />
              <span>PICK</span>
            </h4>
            <p className="ff60-share-sub">
              Show your friends what FilmFind chose for you in 60 seconds.
            </p>

            <div className="ff60-share-card">
              <p className="ff60-share-eyebrow">✦ FilmFind picked this for me in 60 seconds</p>
              <p className="ff60-share-card-title">{resolvedMovie.title.toUpperCase()}</p>
              <p className="ff60-share-reason">{resultWhy[0] ?? "A perfect pick in under 60 seconds."}</p>
              <div className="ff60-share-footer">
                <span>
                  Mood: {activeMood.label} · {formatContextLabel(activeContext.key)} · {formatCravingLabel(activeCraving.key)}
                </span>
                <span className="ff60-share-logo">
                  Film<span>Find</span>
                </span>
              </div>
            </div>

            <div className="ff60-share-actions">
              <button type="button" className="ff60-share-btn" onClick={shareToX}>
                𝕏 Post
              </button>
              <button type="button" className="ff60-share-btn" onClick={shareNative}>
                📷 Story
              </button>
              <button type="button" className="ff60-share-btn" onClick={shareNative}>
                💬 Share
              </button>
              <button type="button" className="ff60-share-btn" onClick={copyShareLink}>
                🔗 Link
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
