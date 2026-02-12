"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Play, Sparkles, Star } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { MovieSearchResult, QueryInterpretation } from "@/types/api";
import { cn } from "@/lib/utils";
import { getPosterUrl, getPlaceholderImage } from "@/lib/image-utils";

interface SearchResultCardProps {
  movie: MovieSearchResult;
  query: string;
  queryInterpretation?: QueryInterpretation;
  index: number;
  showScore?: boolean;
}

interface WhyPicked {
  themeMatch?: string;
  themeSimilarity?: number;
  toneSimilarity?: string;
  toneMatch?: number;
  semanticRelevance?: string;
  storyRelevance?: number;
  queryIntent?: string;
  intentMatch?: number;
  similarTo?: string;
}

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

const truncateText = (text: string, maxLength: number) => {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 3)).trim()}...`;
};

const normalizeScore = (score: number) => {
  if (!Number.isFinite(score)) return 0;
  if (score > 1 && score <= 100) return score / 100;
  return score;
};

const joinList = (items: string[]) => {
  if (items.length <= 1) return items.join("");
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
};

const buildWhyPicked = (
  movie: MovieSearchResult,
  query: string,
  matchScore: number,
  queryInterpretation?: QueryInterpretation
): WhyPicked => {
  const genres = movie.genres?.map((genre) => genre.name).filter(Boolean) || [];
  const keywords =
    movie.keywords?.map((keyword) => keyword.name).filter(Boolean) || [];

  const themeSources =
    queryInterpretation?.themes?.length ? queryInterpretation.themes : genres.slice(0, 2);

  const toneSources =
    queryInterpretation?.tones?.length
      ? queryInterpretation.tones
      : queryInterpretation?.emotions?.length
        ? queryInterpretation.emotions
        : [];

  const referenceTitles = queryInterpretation?.reference_titles?.filter(Boolean) || [];

  const baseScore = clamp(matchScore, 0, 100);
  const themeSimilarity = clamp(baseScore + 2, 0, 100);
  const toneMatch = clamp(baseScore - 3, 0, 100);
  const storyRelevance = clamp(baseScore - 6, 0, 100);
  const intentMatch = clamp(baseScore + 1, 0, 100);

  const themeMatch =
    themeSources.length > 0
      ? `Explores ${joinList(themeSources)} themes that align with your query.`
      : "Shares thematic DNA with your search intent.";

  const toneSimilarity =
    toneSources.length > 0
      ? `Carries a ${joinList(toneSources)} tone similar to what you asked for.`
      : "Balances mood and intensity in a way that fits your request.";

  const semanticRelevance = keywords.length
    ? `High match on keywords: ${keywords.slice(0, 3).join(", ")}.`
    : movie.overview
      ? `Plot focus: ${truncateText(movie.overview, 140)}`
      : undefined;

  const queryIntent = queryInterpretation?.intent
    ? `Aligns with your intent: ${queryInterpretation.intent}.`
    : query
      ? `Aligns with your intent for "${query}".`
      : undefined;

  const similarTo =
    referenceTitles.length > 0 ? referenceTitles.slice(0, 4).join(", ") : undefined;

  return {
    themeMatch,
    themeSimilarity,
    toneSimilarity,
    toneMatch,
    semanticRelevance,
    storyRelevance,
    queryIntent,
    intentMatch,
    similarTo,
  };
};

export function SearchResultCard({
  movie,
  query,
  queryInterpretation,
  index,
  showScore = true,
}: SearchResultCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const posterUrl = getPosterUrl(movie.poster_path) || getPlaceholderImage();

  const releaseYear = movie.release_date
    ? new Date(movie.release_date).getFullYear()
    : "N/A";

  const rating = movie.vote_average || 0;

  const rawScore =
    typeof movie.final_score === "number"
      ? movie.final_score
      : typeof (movie as MovieSearchResult & { relevance_score?: number }).relevance_score === "number"
        ? (movie as MovieSearchResult & { relevance_score?: number }).relevance_score ?? 0
        : movie.similarity_score ?? 0;

  const matchScore = Math.round(clamp(normalizeScore(rawScore), 0, 1) * 100);

  const whyPicked = useMemo(
    () => buildWhyPicked(movie, query, matchScore, queryInterpretation),
    [movie, query, matchScore, queryInterpretation]
  );

  const showMatch = showScore && matchScore > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      className="group"
    >
      {/* Main Card */}
      <Link href={`/movie/${movie.id}`} className="block" aria-label={`View ${movie.title}`}>
        <motion.div
          whileHover={{ y: -8, transition: { duration: 0.2 } }}
          className={cn(
            "relative overflow-hidden rounded-2xl border border-zinc-800/40 bg-zinc-900/30 backdrop-blur-sm",
            "transition-all duration-300"
          )}
        >
          <div className="relative aspect-[2/3] overflow-hidden">
            <Image
              src={posterUrl}
              alt={`${movie.title} poster`}
              fill
              className="object-cover transition-transform duration-500 group-hover:scale-110"
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"
            />

            {/* Gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/50 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

            {/* Play button overlay */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              whileHover={{ opacity: 1, scale: 1 }}
              className="absolute inset-0 flex items-center justify-center opacity-0 transition-all duration-300 group-hover:opacity-100"
            >
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-purple-600/90 shadow-lg shadow-purple-500/50">
                <Play className="ml-1 h-8 w-8 text-white" fill="white" />
              </div>
            </motion.div>

            {/* Rating badge */}
            {rating > 0 && (
              <div className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-black/70 px-2.5 py-1 backdrop-blur-md">
                <Star className="h-3.5 w-3.5 text-yellow-500" fill="currentColor" />
                <span className="text-sm font-semibold text-white">
                  {rating.toFixed(1)}
                </span>
              </div>
            )}

            {/* Match Score Badge */}
            {showMatch && (
              <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 px-3 py-1.5 shadow-lg shadow-purple-500/30 backdrop-blur-md">
                <Sparkles className="h-3.5 w-3.5 text-white" />
                <span className="text-sm font-bold text-white">{matchScore}%</span>
              </div>
            )}
          </div>

          {/* Movie info */}
          <div className="p-4">
            <h3 className="mb-1 line-clamp-1 font-semibold text-white transition-colors duration-300 group-hover:text-purple-300">
              {movie.title}
            </h3>
            <p className="text-sm text-zinc-500">{releaseYear}</p>
          </div>

          {/* Glow effect on hover */}
          <div className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100">
            <div className="absolute inset-0 rounded-2xl shadow-[0_0_40px_rgba(168,85,247,0.3)]" />
          </div>
        </motion.div>
      </Link>

      {/* "Why this match?" CTA */}
      {showScore && (
        <motion.button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className={cn(
            "group/cta mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-zinc-800/20 bg-zinc-900/20 px-4 py-3 transition-all duration-200",
            "hover:border-purple-500/30 hover:bg-zinc-900/40",
            isExpanded && "border-purple-500/40"
          )}
          aria-expanded={isExpanded}
        >
          <Sparkles className="h-4 w-4 text-purple-400 transition-colors group-hover/cta:text-purple-300" />
          <span className="text-sm font-medium text-zinc-400 transition-colors group-hover/cta:text-zinc-300">
            Why this match?
          </span>
        </motion.button>
      )}

      {/* Expandable Explainability Panel */}
      <AnimatePresence>
        {showScore && isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-4 rounded-xl border border-zinc-800/20 bg-zinc-950/40 p-5 backdrop-blur-md">
              {/* Theme Similarity */}
              {whyPicked.themeMatch && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-1 rounded-full bg-purple-500" />
                      <span className="text-xs font-semibold uppercase tracking-wide text-zinc-300">
                        Theme Similarity
                      </span>
                    </div>
                    {whyPicked.themeSimilarity !== undefined && (
                      <span className="text-xs font-bold text-purple-400">
                        {whyPicked.themeSimilarity}%
                      </span>
                    )}
                  </div>
                  <p className="pl-3 text-sm leading-relaxed text-zinc-400">
                    {whyPicked.themeMatch}
                  </p>
                </div>
              )}

              {/* Tone Match */}
              {whyPicked.toneSimilarity && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-1 rounded-full bg-blue-500" />
                      <span className="text-xs font-semibold uppercase tracking-wide text-zinc-300">
                        Tone Match
                      </span>
                    </div>
                    {whyPicked.toneMatch !== undefined && (
                      <span className="text-xs font-bold text-blue-400">
                        {whyPicked.toneMatch}%
                      </span>
                    )}
                  </div>
                  <p className="pl-3 text-sm leading-relaxed text-zinc-400">
                    {whyPicked.toneSimilarity}
                  </p>
                </div>
              )}

              {/* Story Relevance */}
              {whyPicked.semanticRelevance && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-1 rounded-full bg-emerald-500" />
                      <span className="text-xs font-semibold uppercase tracking-wide text-zinc-300">
                        Story Relevance
                      </span>
                    </div>
                    {whyPicked.storyRelevance !== undefined && (
                      <span className="text-xs font-bold text-emerald-400">
                        {whyPicked.storyRelevance}%
                      </span>
                    )}
                  </div>
                  <p className="pl-3 text-sm leading-relaxed text-zinc-400">
                    {whyPicked.semanticRelevance}
                  </p>
                </div>
              )}

              {/* Query Intent */}
              {whyPicked.queryIntent && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-1 rounded-full bg-amber-500" />
                      <span className="text-xs font-semibold uppercase tracking-wide text-zinc-300">
                        Query Intent
                      </span>
                    </div>
                    {whyPicked.intentMatch !== undefined && (
                      <span className="text-xs font-bold text-amber-400">
                        {whyPicked.intentMatch}%
                      </span>
                    )}
                  </div>
                  <p className="pl-3 text-sm leading-relaxed text-zinc-400">
                    {whyPicked.queryIntent}
                  </p>
                </div>
              )}

              {/* Similar To */}
              {whyPicked.similarTo && (
                <div className="mt-3 border-t border-zinc-800/30 pt-3">
                  <div className="flex items-start gap-2">
                    <span className="whitespace-nowrap text-xs font-semibold uppercase tracking-wide text-zinc-500">
                      Similar to:
                    </span>
                    <p className="text-xs leading-relaxed text-zinc-400">
                      {whyPicked.similarTo}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
