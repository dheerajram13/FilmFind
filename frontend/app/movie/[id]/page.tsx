"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { ArrowLeft, Star, Calendar, Clock, Globe } from "lucide-react";
import apiClient, { APIError } from "@/lib/api-client";
import { Movie, SimilarMoviesResponse } from "@/types/api";
import { CastCarousel } from "@/components/CastCarousel";
import { SimilarMovies } from "@/components/SimilarMovies";
import { StreamingProviders } from "@/components/StreamingProviders";
import { ErrorState } from "@/components/ErrorState";

export default function MovieDetailPage() {
  const params = useParams();
  const router = useRouter();
  const movieId = Number(params.id);

  const [movie, setMovie] = useState<Movie | null>(null);
  const [similarMovies, setSimilarMovies] = useState<SimilarMoviesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchMovieData = async () => {
      if (!movieId || isNaN(movieId)) {
        setError(new Error("Invalid movie ID"));
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        // Fetch movie details and similar movies in parallel
        const [movieData, similarData] = await Promise.all([
          apiClient.getMovie(movieId) as Promise<Movie>,
          apiClient.getSimilarMovies(movieId, 0, 12) as Promise<SimilarMoviesResponse>,
        ]);

        setMovie(movieData);
        setSimilarMovies(similarData);
      } catch (err) {
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
        setIsLoading(false);
      }
    };

    fetchMovieData();
  }, [movieId]);

  const handleRetry = () => {
    window.location.reload();
  };

  const handleGoBack = () => {
    router.back();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="mx-auto max-w-7xl px-4 py-8">
          <div className="animate-pulse">
            <div className="h-96 bg-gray-300 dark:bg-gray-700 rounded-lg mb-8" />
            <div className="h-12 bg-gray-300 dark:bg-gray-700 rounded mb-4 w-3/4" />
            <div className="h-6 bg-gray-300 dark:bg-gray-700 rounded mb-8 w-1/2" />
            <div className="h-32 bg-gray-300 dark:bg-gray-700 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="mx-auto max-w-7xl px-4 py-8">
          <button
            onClick={handleGoBack}
            className="mb-4 flex items-center gap-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
          >
            <ArrowLeft size={20} />
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Backdrop */}
      {backdropUrl && (
        <div className="relative h-96 w-full">
          <div className="absolute inset-0 bg-gradient-to-t from-gray-50 via-gray-50/80 to-transparent dark:from-gray-900 dark:via-gray-900/80 z-10" />
          <Image
            src={backdropUrl}
            alt={movie.title}
            fill
            className="object-cover"
            priority
          />
        </div>
      )}

      {/* Content */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Back Button */}
        <button
          onClick={handleGoBack}
          className="mb-6 flex items-center gap-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 transition-colors"
        >
          <ArrowLeft size={20} />
          Back to results
        </button>

        {/* Movie Header */}
        <div className="flex flex-col md:flex-row gap-8 mb-12">
          {/* Poster */}
          {posterUrl && (
            <div className="flex-shrink-0">
              <div className="relative w-64 aspect-[2/3] rounded-lg overflow-hidden shadow-xl">
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

          {/* Movie Info */}
          <div className="flex-1">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              {movie.title}
            </h1>

            {movie.tagline && (
              <p className="text-xl text-gray-600 dark:text-gray-400 italic mb-4">
                {movie.tagline}
              </p>
            )}

            {/* Metadata */}
            <div className="flex flex-wrap items-center gap-4 text-gray-700 dark:text-gray-300 mb-6">
              {/* Rating */}
              <div className="flex items-center gap-1">
                <Star className="fill-yellow-400 text-yellow-400" size={20} />
                <span className="font-semibold text-lg">
                  {movie.vote_average ? movie.vote_average.toFixed(1) : "N/A"}
                </span>
                <span className="text-sm text-gray-500">
                  ({movie.vote_count?.toLocaleString()} votes)
                </span>
              </div>

              {/* Year */}
              {releaseYear && (
                <>
                  <span className="text-gray-400">•</span>
                  <div className="flex items-center gap-1">
                    <Calendar size={18} />
                    <span>{releaseYear}</span>
                  </div>
                </>
              )}

              {/* Runtime */}
              {formattedRuntime && (
                <>
                  <span className="text-gray-400">•</span>
                  <div className="flex items-center gap-1">
                    <Clock size={18} />
                    <span>{formattedRuntime}</span>
                  </div>
                </>
              )}

              {/* Language */}
              {movie.original_language && (
                <>
                  <span className="text-gray-400">•</span>
                  <div className="flex items-center gap-1">
                    <Globe size={18} />
                    <span className="uppercase">{movie.original_language}</span>
                  </div>
                </>
              )}
            </div>

            {/* Genres */}
            {movie.genres && movie.genres.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-6">
                {movie.genres.map((genre) => (
                  <span
                    key={genre.id}
                    className="rounded-full bg-blue-100 px-4 py-1.5 text-sm font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                  >
                    {genre.name}
                  </span>
                ))}
              </div>
            )}

            {/* Overview */}
            {movie.overview && (
              <div className="mb-6">
                <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-3">
                  Overview
                </h2>
                <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                  {movie.overview}
                </p>
              </div>
            )}

            {/* Keywords */}
            {movie.keywords && movie.keywords.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Keywords
                </h3>
                <div className="flex flex-wrap gap-2">
                  {movie.keywords.slice(0, 10).map((keyword) => (
                    <span
                      key={keyword.id}
                      className="rounded-md bg-gray-200 px-3 py-1 text-sm text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                    >
                      {keyword.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Streaming Providers */}
        {movie.streaming_providers && (
          <div className="mb-12">
            <StreamingProviders providers={movie.streaming_providers} />
          </div>
        )}

        {/* Cast */}
        {movie.cast_members && movie.cast_members.length > 0 && (
          <div className="mb-12">
            <CastCarousel cast={movie.cast_members} />
          </div>
        )}

        {/* Similar Movies */}
        {similarMovies && similarMovies.similar_movies.length > 0 && (
          <div className="mb-12">
            <SimilarMovies movies={similarMovies.similar_movies} />
          </div>
        )}
      </div>
    </div>
  );
}
