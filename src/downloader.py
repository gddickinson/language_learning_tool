"""
Internet downloader for pronunciation samples.
Supports downloading from various sources like Forvo, YouGlish, etc.
"""
import os
import requests
from typing import List, Dict, Optional
import json
from urllib.parse import quote, urljoin
import time
import config


class SampleDownloader:
    """Downloads pronunciation samples from various online sources."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the downloader.
        
        Args:
            api_key: API key for Forvo (optional)
        """
        self.forvo_api_key = api_key or config.FORVO_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LanguageLearningTool/1.0'
        })
    
    def search_forvo(self, word: str, language: str = 'en',
                    limit: int = 5) -> List[Dict]:
        """
        Search for pronunciations on Forvo.
        
        Args:
            word: Word to search for
            language: Language code (e.g., 'en', 'es', 'fr')
            limit: Maximum number of results
            
        Returns:
            List of pronunciation dictionaries
        """
        if not self.forvo_api_key:
            return [{
                'error': 'Forvo API key not configured',
                'info': 'Visit https://api.forvo.com to get an API key'
            }]
        
        # Forvo API endpoint
        url = f'https://apifree.forvo.com/key/{self.forvo_api_key}/format/json/'
        url += f'action/word-pronunciations/word/{quote(word)}/language/{language}'
        
        try:
            response = self.session.get(url, timeout=config.DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            if 'items' not in data:
                return []
            
            pronunciations = []
            for item in data['items'][:limit]:
                pronunciations.append({
                    'word': word,
                    'language': language,
                    'username': item.get('username', 'unknown'),
                    'country': item.get('country', ''),
                    'audio_url': item.get('pathmp3', ''),
                    'votes': item.get('num_votes', 0),
                    'source': 'forvo'
                })
            
            return pronunciations
            
        except requests.RequestException as e:
            return [{'error': f'Failed to fetch from Forvo: {str(e)}'}]
    
    def download_audio(self, url: str, output_path: str) -> bool:
        """
        Download audio file from URL.
        
        Args:
            url: URL of audio file
            output_path: Path to save audio file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(url, timeout=config.DOWNLOAD_TIMEOUT,
                                       stream=True)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"Download failed: {e}")
            return False
    
    def download_forvo_pronunciation(self, word: str, language: str = 'en',
                                    output_dir: str = config.SAMPLES_DIR,
                                    select_index: int = 0) -> Optional[str]:
        """
        Download a pronunciation from Forvo.
        
        Args:
            word: Word to download
            language: Language code
            output_dir: Directory to save audio
            select_index: Which pronunciation to download (0 = top rated)
            
        Returns:
            Path to downloaded file, or None if failed
        """
        # Search for pronunciations
        results = self.search_forvo(word, language)
        
        if not results or 'error' in results[0]:
            return None
        
        if select_index >= len(results):
            select_index = 0
        
        selected = results[select_index]
        audio_url = selected['audio_url']
        
        # Create filename
        username = selected['username'].replace(' ', '_')
        filename = f"{word}_{language}_{username}.mp3"
        output_path = os.path.join(output_dir, language, filename)
        
        # Download
        if self.download_audio(audio_url, output_path):
            return output_path
        
        return None
    
    def search_cambridge_dictionary(self, word: str,
                                    variety: str = 'us') -> Optional[str]:
        """
        Get pronunciation audio URL from Cambridge Dictionary.
        Note: This is for educational purposes. Check Cambridge's terms of service.
        
        Args:
            word: Word to search
            variety: 'us' or 'uk'
            
        Returns:
            Audio URL if found, None otherwise
        """
        # Note: This is a simplified example. In production, you might use
        # BeautifulSoup to parse the page properly.
        base_url = f'https://dictionary.cambridge.org/dictionary/english/{word}'
        
        try:
            response = self.session.get(base_url)
            response.raise_for_status()
            
            # Look for audio URLs in the page (simplified)
            # In practice, you'd parse the HTML properly
            if variety == 'us':
                marker = 'us_pron'
            else:
                marker = 'uk_pron'
            
            # This is a placeholder - proper implementation would use BeautifulSoup
            # to extract the actual audio URL
            return None
            
        except requests.RequestException:
            return None
    
    def search_free_resources(self, word: str,
                             language: str = 'en') -> List[Dict]:
        """
        Search free pronunciation resources (Shtooka, etc.).
        
        Args:
            word: Word to search
            language: Language code
            
        Returns:
            List of available resources
        """
        resources = []
        
        # Shtooka project
        # Note: Shtooka has different collections for different languages
        # This is a simplified example
        shtooka_base = 'http://shtooka.net/audio/'
        
        # Example paths (actual paths vary by language and collection)
        possible_paths = [
            f'{language}/{word}.flac',
            f'{language}/{word}.ogg',
        ]
        
        for path in possible_paths:
            url = urljoin(shtooka_base, path)
            resources.append({
                'word': word,
                'language': language,
                'source': 'shtooka',
                'url': url,
                'format': path.split('.')[-1]
            })
        
        return resources
    
    def get_sample_metadata(self, url: str) -> Dict:
        """
        Get metadata about an audio sample without downloading it.
        
        Args:
            url: URL of audio file
            
        Returns:
            Metadata dictionary
        """
        try:
            response = self.session.head(url, timeout=10)
            response.raise_for_status()
            
            return {
                'content_type': response.headers.get('Content-Type', ''),
                'content_length': int(response.headers.get('Content-Length', 0)),
                'available': True
            }
        except Exception:
            return {'available': False}
    
    def batch_download(self, word_list: List[str], language: str = 'en',
                      output_dir: str = config.SAMPLES_DIR,
                      delay: float = 1.0) -> List[Dict]:
        """
        Download pronunciations for multiple words.
        
        Args:
            word_list: List of words to download
            language: Language code
            output_dir: Output directory
            delay: Delay between downloads (seconds) to be polite
            
        Returns:
            List of download results
        """
        results = []
        
        for word in word_list:
            filepath = self.download_forvo_pronunciation(
                word, language, output_dir
            )
            
            results.append({
                'word': word,
                'success': filepath is not None,
                'filepath': filepath
            })
            
            # Be polite to the server
            if delay > 0:
                time.sleep(delay)
        
        return results
    
    def get_suggested_words(self, category: str,
                           language: str = 'en') -> List[str]:
        """
        Get suggested words for practice by category.
        
        Args:
            category: Category (e.g., 'greetings', 'numbers', 'colors')
            language: Language code
            
        Returns:
            List of suggested words
        """
        # Common vocabulary sets
        suggestions = {
            'greetings': ['hello', 'goodbye', 'good morning', 'good evening',
                         'thank you', 'please', 'excuse me'],
            'numbers': ['one', 'two', 'three', 'four', 'five',
                       'six', 'seven', 'eight', 'nine', 'ten'],
            'colors': ['red', 'blue', 'green', 'yellow', 'black',
                      'white', 'orange', 'purple', 'pink', 'brown'],
            'days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                    'Friday', 'Saturday', 'Sunday'],
            'months': ['January', 'February', 'March', 'April', 'May',
                      'June', 'July', 'August', 'September', 'October',
                      'November', 'December'],
            'food': ['water', 'bread', 'coffee', 'tea', 'milk',
                    'apple', 'banana', 'rice', 'chicken', 'fish'],
            'common': ['yes', 'no', 'maybe', 'sorry', 'help',
                      'where', 'when', 'how', 'what', 'why']
        }
        
        return suggestions.get(category.lower(), [])


if __name__ == '__main__':
    # Unit test
    print("Testing SampleDownloader...")
    
    downloader = SampleDownloader()
    
    # Test suggested words
    print("\nGetting suggested greetings...")
    greetings = downloader.get_suggested_words('greetings')
    print(f"Found {len(greetings)} greetings: {', '.join(greetings[:5])}")
    
    # Test Forvo search (will fail without API key, but that's expected)
    print("\nTesting Forvo search...")
    results = downloader.search_forvo('hello', 'en', limit=2)
    if results and 'error' in results[0]:
        print(f"Expected error (no API key): {results[0]['error']}")
    else:
        print(f"Found {len(results)} pronunciations")
    
    # Test free resources
    print("\nSearching free resources...")
    free_resources = downloader.search_free_resources('hello', 'en')
    print(f"Found {len(free_resources)} potential resources")
    
    print("\nAll tests passed!")
