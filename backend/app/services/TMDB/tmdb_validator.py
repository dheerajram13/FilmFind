"""
TMDB Data Validator
"""
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger


class TMDBDataValidator:
    """
    Validates and cleans TMDB data (SRP)
    """

    @staticmethod
    def validate_movie(movie_data: Dict[str, Any]) -> bool:
        """
        Validate that movie data has required fields

        Args:
            movie_data: Raw movie data from TMDB

        Returns:
            True if valid, False otherwise
        """

        required_fields = ['id', 'title']

        return all(field in movie_data and movie_data[field] for field in required_fields)

    @staticmethod
    def clean_movie_data(movie_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize movie data

        Args:
            movie_data: Raw movie data from TMDB

        Returns:
            Cleaned movie data
        """

        cleaned = {
            'tmdb_id': movie_data.get('id'),
            'title': movie_data.get('title', '').strip(),
            'original_title': movie_data.get('original_title', '').strip(),
            'overview': movie_data.get('overview', '').strip(),
            'tagline': movie_data.get('tagline', '').strip(),
            'release_date': TMDBDataValidator._parse_date(movie_data.get('release_date')),
            'runtime': movie_data.get('runtime'),
            'adult': movie_data.get('adult', False),
            'popularity': movie_data.get('popularity', 0.0),
            'vote_average': movie_data.get('vote_average', 0.0),
            'vote_count': movie_data.get('vote_count', 0),
            'original_language': movie_data.get('original_language', ''),
            'poster_path': movie_data.get('poster_path'),
            'backdrop_path': movie_data.get('backdrop_path'),
            'status': movie_data.get('status'),
            'budget': movie_data.get('budget', 0),
            'revenue': movie_data.get('revenue', 0),
            'imdb_id': movie_data.get('imdb_id'),
            'genres': [g['name'] for g in movie_data.get('genres', [])],
            'genre_ids': [g['id'] for g in movie_data.get('genres', [])],
        }

        # Extract keywords if available
        if 'keywords' in movie_data:
            cleaned['keywords'] = [
                {'id': kw['id'], 'name': kw['name']}
                for kw in movie_data['keywords'].get('keywords', [])
            ]

        # Extract cast if available
        if 'credits' in movie_data:
            cleaned['cast'] = [
                {
                    'id': cast['id'],
                    'name': cast['name'],
                    'character': cast.get('character', ''),
                    'order': cast.get('order', 999),
                    'profile_path': cast.get('profile_path')
                }
                for cast in movie_data['credits'].get('cast', [])[:10]  # Top 10 cast
            ]

        return cleaned

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""

        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
            return None

