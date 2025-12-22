"""
Database manager for storing and retrieving pronunciation samples.
Uses SQLite for local storage of audio samples and metadata.
"""
import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np
import config


class DatabaseManager:
    """Manages the SQLite database for pronunciation samples."""
    
    def __init__(self, db_path: str = config.DB_PATH):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Samples table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                language TEXT NOT NULL,
                filepath TEXT NOT NULL,
                source TEXT,
                speaker TEXT,
                category TEXT,
                duration REAL,
                sample_rate INTEGER,
                added_date TEXT,
                metadata TEXT
            )
        ''')
        
        # User recordings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                language TEXT NOT NULL,
                filepath TEXT NOT NULL,
                reference_id INTEGER,
                similarity_score REAL,
                feedback TEXT,
                recorded_date TEXT,
                FOREIGN KEY (reference_id) REFERENCES samples(id)
            )
        ''')
        
        # Practice history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS practice_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                language TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                best_score REAL,
                last_practiced TEXT,
                notes TEXT
            )
        ''')
        
        # Categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                parent_category TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_sample(self, word: str, language: str, filepath: str,
                  source: str = 'user', speaker: str = '',
                  category: str = '', duration: float = 0,
                  sample_rate: int = 44100,
                  metadata: Optional[Dict] = None) -> int:
        """
        Add a pronunciation sample to the database.
        
        Args:
            word: The word or phrase
            language: Language code (e.g., 'en', 'es', 'fr')
            filepath: Path to audio file
            source: Source of sample ('user', 'forvo', 'downloaded', etc.)
            speaker: Speaker name/ID
            category: Category (e.g., 'greetings', 'numbers')
            duration: Audio duration in seconds
            sample_rate: Sample rate in Hz
            metadata: Additional metadata as dictionary
            
        Returns:
            ID of inserted sample
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else '{}'
        added_date = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO samples
            (word, language, filepath, source, speaker, category,
             duration, sample_rate, added_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (word, language, filepath, source, speaker, category,
              duration, sample_rate, added_date, metadata_json))
        
        sample_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return sample_id
    
    def add_user_recording(self, word: str, language: str, filepath: str,
                          reference_id: Optional[int] = None,
                          similarity_score: Optional[float] = None,
                          feedback: str = '') -> int:
        """
        Add a user's pronunciation recording.
        
        Args:
            word: The word/phrase pronounced
            language: Language code
            filepath: Path to recorded audio
            reference_id: ID of reference sample (if compared)
            similarity_score: Similarity score (0-100)
            feedback: Textual feedback
            
        Returns:
            ID of inserted recording
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        recorded_date = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO user_recordings
            (word, language, filepath, reference_id, similarity_score,
             feedback, recorded_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (word, language, filepath, reference_id, similarity_score,
              feedback, recorded_date))
        
        recording_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Update practice history
        self._update_practice_history(word, language, similarity_score)
        
        return recording_id
    
    def _update_practice_history(self, word: str, language: str,
                                 score: Optional[float] = None):
        """Update practice history for a word."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if entry exists
        cursor.execute('''
            SELECT id, attempts, best_score FROM practice_history
            WHERE word = ? AND language = ?
        ''', (word, language))
        
        result = cursor.fetchone()
        current_date = datetime.now().isoformat()
        
        if result:
            history_id, attempts, best_score = result
            new_attempts = attempts + 1
            new_best_score = best_score
            
            if score is not None:
                if best_score is None or score > best_score:
                    new_best_score = score
            
            cursor.execute('''
                UPDATE practice_history
                SET attempts = ?, best_score = ?, last_practiced = ?
                WHERE id = ?
            ''', (new_attempts, new_best_score, current_date, history_id))
        else:
            cursor.execute('''
                INSERT INTO practice_history
                (word, language, attempts, best_score, last_practiced)
                VALUES (?, ?, 1, ?, ?)
            ''', (word, language, score, current_date))
        
        conn.commit()
        conn.close()
    
    def get_samples(self, word: Optional[str] = None,
                   language: Optional[str] = None,
                   category: Optional[str] = None,
                   source: Optional[str] = None) -> List[Dict]:
        """
        Retrieve samples from database.
        
        Args:
            word: Filter by word (optional)
            language: Filter by language (optional)
            category: Filter by category (optional)
            source: Filter by source (optional)
            
        Returns:
            List of sample dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM samples WHERE 1=1'
        params = []
        
        if word:
            query += ' AND word = ?'
            params.append(word)
        if language:
            query += ' AND language = ?'
            params.append(language)
        if category:
            query += ' AND category = ?'
            params.append(category)
        if source:
            query += ' AND source = ?'
            params.append(source)
        
        query += ' ORDER BY added_date DESC'
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        samples = []
        for row in rows:
            sample = dict(zip(columns, row))
            # Parse metadata JSON
            if sample['metadata']:
                sample['metadata'] = json.loads(sample['metadata'])
            samples.append(sample)
        
        return samples
    
    def get_user_recordings(self, word: Optional[str] = None,
                           limit: int = 50) -> List[Dict]:
        """
        Get user's pronunciation recordings.
        
        Args:
            word: Filter by word (optional)
            limit: Maximum number of results
            
        Returns:
            List of recording dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM user_recordings WHERE 1=1'
        params = []
        
        if word:
            query += ' AND word = ?'
            params.append(word)
        
        query += ' ORDER BY recorded_date DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_practice_history(self, word: Optional[str] = None) -> List[Dict]:
        """
        Get practice history.
        
        Args:
            word: Filter by word (optional)
            
        Returns:
            List of practice history entries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if word:
            cursor.execute('''
                SELECT * FROM practice_history
                WHERE word = ?
                ORDER BY last_practiced DESC
            ''', (word,))
        else:
            cursor.execute('''
                SELECT * FROM practice_history
                ORDER BY last_practiced DESC
            ''')
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def delete_sample(self, sample_id: int) -> bool:
        """
        Delete a sample from database.
        
        Args:
            sample_id: ID of sample to delete
            
        Returns:
            True if deleted, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get filepath first to delete file
        cursor.execute('SELECT filepath FROM samples WHERE id = ?', (sample_id,))
        result = cursor.fetchone()
        
        if result:
            filepath = result[0]
            # Delete from database
            cursor.execute('DELETE FROM samples WHERE id = ?', (sample_id,))
            conn.commit()
            conn.close()
            
            # Delete file if it exists
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return True
        
        conn.close()
        return False
    
    def search_samples(self, search_term: str) -> List[Dict]:
        """
        Search samples by word or category.
        
        Args:
            search_term: Search term
            
        Returns:
            List of matching samples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM samples
            WHERE word LIKE ? OR category LIKE ?
            ORDER BY word
        ''', (f'%{search_term}%', f'%{search_term}%'))
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_statistics(self) -> Dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary of statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total samples
        cursor.execute('SELECT COUNT(*) FROM samples')
        stats['total_samples'] = cursor.fetchone()[0]
        
        # Total user recordings
        cursor.execute('SELECT COUNT(*) FROM user_recordings')
        stats['total_recordings'] = cursor.fetchone()[0]
        
        # Languages
        cursor.execute('SELECT DISTINCT language FROM samples')
        stats['languages'] = [row[0] for row in cursor.fetchall()]
        
        # Categories
        cursor.execute('SELECT DISTINCT category FROM samples WHERE category != ""')
        stats['categories'] = [row[0] for row in cursor.fetchall()]
        
        # Most practiced words
        cursor.execute('''
            SELECT word, attempts, best_score
            FROM practice_history
            ORDER BY attempts DESC
            LIMIT 10
        ''')
        stats['most_practiced'] = [
            {'word': row[0], 'attempts': row[1], 'best_score': row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return stats
    
    def add_category(self, name: str, description: str = '',
                    parent: Optional[str] = None) -> int:
        """Add a category to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO categories (name, description, parent_category)
                VALUES (?, ?, ?)
            ''', (name, description, parent))
            category_id = cursor.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            # Category already exists
            cursor.execute('SELECT id FROM categories WHERE name = ?', (name,))
            category_id = cursor.fetchone()[0]
        
        conn.close()
        return category_id


if __name__ == '__main__':
    # Unit test
    print("Testing DatabaseManager...")
    
    # Use test database
    test_db = os.path.join(config.TEMP_DIR, 'test.db')
    db = DatabaseManager(test_db)
    
    # Add sample
    print("\nAdding sample...")
    sample_id = db.add_sample(
        word='hello',
        language='en',
        filepath='/tmp/hello.wav',
        source='test',
        speaker='TestSpeaker',
        category='greetings',
        duration=1.5,
        metadata={'accent': 'american'}
    )
    print(f"Added sample ID: {sample_id}")
    
    # Get samples
    print("\nRetrieving samples...")
    samples = db.get_samples(word='hello')
    print(f"Found {len(samples)} sample(s)")
    print(f"Sample data: {samples[0]['word']} ({samples[0]['language']})")
    
    # Add user recording
    print("\nAdding user recording...")
    recording_id = db.add_user_recording(
        word='hello',
        language='en',
        filepath='/tmp/user_hello.wav',
        reference_id=sample_id,
        similarity_score=85.5,
        feedback='Good pronunciation!'
    )
    print(f"Added recording ID: {recording_id}")
    
    # Get statistics
    print("\nGetting statistics...")
    stats = db.get_statistics()
    print(f"Total samples: {stats['total_samples']}")
    print(f"Total recordings: {stats['total_recordings']}")
    
    # Cleanup
    os.remove(test_db)
    print("\nAll tests passed!")
