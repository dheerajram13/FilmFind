"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { ArrowLeft, Star, Calendar, Clock, Globe } from "lucide-react";
import apiClient, { APIError } from "@/lib/api-client";
import { Movie, SimilarMoviesResponse } from "@/types/api";
import { CastCarousel } from "@/components/movie/CastCarousel";
import { SimilarMovies } from "@/components/movie/SimilarMovies";
import { StreamingProviders } from "@/components/movie/StreamingProviders";
import { ErrorState } from "@/components/feedback/ErrorState";

export default function MovieDetailPage() {
  const params = useParams();
  const router = useRouter();
  const movieId = Number(params.id);

  const [movie, setMovie] = useState<Movie | null>(null);
  const [similarMovies, setSimilarMovies] = useState<SimilarMoviesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const isMounted = useRef(true);

  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);

  const fetchMovieData = useCallback(async () => {
    if (!movieId || Number.isNaN(movieId)) {
      if (isMounted.current) {
        setError(new Error("Invalid movie ID"));
        setIsLoading(false);
      }
      return;
    }

    if (isMounted.current) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const [movieData, similarData] = await Promise.all([
        apiClient.getMovie(movieId) as Promise<Movie>,
        apiClient.getSimilarMovies(movieId, 0, 12) as Promise<SimilarMoviesResponse>,
      ]);

      if (!isMounted.current) return;
      setMovie(movieData);
      setSimilarMovies(similarData);
    } catch (err) {
      if (!isMounted.current) return;
      console.error("Error fetching movie data:", err);
      if (err instanceof APIError) {
        if (err.status === 404) {
          setError(new Error("Movie not found"));
        } else {
          setError(new Error(`Failed to load movie: ${err.message}`));
        }
      } else {
        setError(new Error("Failed to load movie. Please try again."));
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, [movieId]);

  useEffect(() => {
    fetchMovieData();
  }, [fetchMovieData]);

  const handleRetry = useCallback(() => {
    fetchMovieData();
  }, [fetchMovieData]);

  const handleGoBack = useCallback(() => {
    router.back();
  }, [router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
          <div className="animate-pulse space-y-6">
            <div className="h-72 rounded-3xl bg-zinc-800/80" />
            <div className="h-12 w-3/4 rounded-2xl bg-zinc-800/80" />
            <div className="h-6 w-1/2 rounded-2xl bg-zinc-800/80" />
            <div className="h-32 rounded-2xl bg-zinc-800/80" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-black">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
          <button
            onClick={handleGoBack}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/60 px-4 py-2 text-sm font-semibold text-zinc-300 transition-colors hover:text-white"
          >
            <ArrowLeft size={18} />
            Go Back
          </button>
          <ErrorState error={error} onRetry={handleRetry} />
        </div>
      </div>
    );
  }

  if (!movie) {
    return null;
  }

  const backdropUrl = movie.backdrop_path
    ? `https://image.tmdb.org/t/p/original${movie.backdrop_path}`
    : null;

  const posterUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : null;

  const releaseYear = movie.release_date
    ? new Date(movie.release_date).getFullYear()
    : null;

  const formattedRuntime = movie.runtime
    ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m`
    : null;

  return (
    <div className="min-h-screen bg-black">
      {backdropUrl && (
        <div className="relative h-[38vh] min-h-[280px] w-full overflow-hidden">
          <Image
            src={backdropUrl}
            alt={movie.title}
            fill
            className="object-cover"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/30 to-black" />
        </div>
      )}

      <div className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        <button
          onClick={handleGoBack}
          className="mt-8 inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/60 px-4 py-2 text-sm font-semibold text-zinc-300 transition-colors hover:text-white"
        >
          <ArrowLeft size={18} />
          Back to results
        </button>

        <div className="mt-6 grid gap-10 lg:grid-cols-[280px_1fr]">
          {posterUrl && (
            <div className="flex-shrink-0">
              <div className="relative w-full max-w-[280px] aspect-[2/3] overflow-hidden rounded-md border border-zinc-800 bg-zinc-900/60">
                <Image
                  src={posterUrl}
                  alt={movie.title}
                  fill
                  className="object-cover"
                  priority
                />
              </div>
            </div>
          )}

          <div className="space-y-6">
            <div>
              <h1 className="text-4xl font-semibold text-white sm:text-5xl">{movie.title}</h1>
              {movie.tagline && (
                <p className="mt-2 text-lg italic text-zinc-400">{movie.tagline}</p>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-400">
              <div className="flex items-center gap-2 rounded-full bg-emerald-500/15 px-3 py-1 text-emerald-300">
                <Star className="fill-emerald-400 text-emerald-400" size={16} />
                <span className="font-semibold">
                  {movie.vote_average ? movie.vote_average.toFixed(1) : "N/A"}
                </span>
                <span className="text-xs text-emerald-300/80">
                  ({movie.vote_count?.toLocaleString()} votes)
                </span>
              </div>

              {releaseYear && (
                <div className="flex items-center gap-1">
                  <Calendar size={16} />
                  <span>{releaseYear}</span>
                </div>
              )}

              {formattedRuntime && (
                <div className="flex items-center gap-1">
                  <Clock size={16} />
                  <span>{formattedRuntime}</span>
                </div>
              )}

              {movie.original_language && (
                <div className="flex items-center gap-1">
                  <Globe size={16} />
                  <span className="uppercase">{movie.original_language}</span>
                </div>
              )}
            </div>

            {movie.genres && movie.genres.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {movie.genres.map((genre) => (
                  <span
                    key={genre.id}
                    className="rounded-full border border-zinc-800 bg-zinc-900/60 px-4 py-1.5 text-xs font-semibold text-zinc-300"
                  >
                    {genre.name}
                  </span>
                ))}
              </div>
            )}

            {movie.overview && (
              <div>
                <h2 className="text-2xl font-semibold text-white">Overview</h2>
                <p className="mt-2 text-zinc-400 leading-relaxed">{movie.overview}</p>
              </div>
            )}

            {movie.keywords && movie.keywords.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-white">Keywords</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {movie.keywords.slice(0, 10).map((keyword) => (
                    <span
                      key={keyword.id}
                      className="rounded-full bg-zinc-900/70 px-3 py-1 text-xs font-medium text-zinc-300"
                    >
                      {keyword.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="mt-12 space-y-12">
          {movie.streaming_providers && (
            <StreamingProviders providers={movie.streaming_providers} />
          )}

          {movie.cast_members && movie.cast_members.length > 0 && (
            <CastCarousel cast={movie.cast_members} />
          )}

          {similarMovies && similarMovies.similar_movies.length > 0 && (
            <SimilarMovies movies={similarMovies.similar_movies} />
          )}
        </div>
      </div>
    </div>
  );
}
