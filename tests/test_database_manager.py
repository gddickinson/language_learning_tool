"""
Unit tests for the DatabaseManager module.
"""
import unittest
import os
import sys
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database_manager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """Test database is created and initialized."""
        self.assertTrue(os.path.exists(self.db_path))
    
    def test_add_sample(self):
        """Test adding a pronunciation sample."""
        sample_id = self.db.add_sample(
            word='hello',
            language='en',
            filepath='/tmp/hello.wav',
            source='test',
            speaker='TestSpeaker',
            category='greetings',
            duration=1.5,
            metadata={'accent': 'american'}
        )
        
        self.assertIsInstance(sample_id, int)
        self.assertGreater(sample_id, 0)
    
    def test_get_samples(self):
        """Test retrieving samples."""
        # Add test samples
        self.db.add_sample('hello', 'en', '/tmp/hello.wav', 'test')
        self.db.add_sample('goodbye', 'en', '/tmp/goodbye.wav', 'test')
        self.db.add_sample('hola', 'es', '/tmp/hola.wav', 'test')
        
        # Get all samples
        all_samples = self.db.get_samples()
        self.assertEqual(len(all_samples), 3)
        
        # Get samples by word
        hello_samples = self.db.get_samples(word='hello')
        self.assertEqual(len(hello_samples), 1)
        self.assertEqual(hello_samples[0]['word'], 'hello')
        
        # Get samples by language
        en_samples = self.db.get_samples(language='en')
        self.assertEqual(len(en_samples), 2)
        
        es_samples = self.db.get_samples(language='es')
        self.assertEqual(len(es_samples), 1)
    
    def test_add_user_recording(self):
        """Test adding user recordings."""
        # Add reference sample first
        ref_id = self.db.add_sample('hello', 'en', '/tmp/hello.wav', 'ref')
        
        # Add user recording
        rec_id = self.db.add_user_recording(
            word='hello',
            language='en',
            filepath='/tmp/user_hello.wav',
            reference_id=ref_id,
            similarity_score=85.5,
            feedback='Good pronunciation!'
        )
        
        self.assertIsInstance(rec_id, int)
        self.assertGreater(rec_id, 0)
        
        # Retrieve recording
        recordings = self.db.get_user_recordings(word='hello')
        self.assertEqual(len(recordings), 1)
        self.assertEqual(recordings[0]['word'], 'hello')
        self.assertAlmostEqual(recordings[0]['similarity_score'], 85.5)
    
    def test_practice_history(self):
        """Test practice history tracking."""
        # Add multiple attempts for same word
        self.db.add_user_recording('hello', 'en', '/tmp/1.wav', 
                                  similarity_score=70.0)
        self.db.add_user_recording('hello', 'en', '/tmp/2.wav',
                                  similarity_score=80.0)
        self.db.add_user_recording('hello', 'en', '/tmp/3.wav',
                                  similarity_score=90.0)
        
        # Get practice history
        history = self.db.get_practice_history(word='hello')
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['word'], 'hello')
        self.assertEqual(history[0]['attempts'], 3)
        self.assertAlmostEqual(history[0]['best_score'], 90.0)
    
    def test_search_samples(self):
        """Test sample search functionality."""
        # Add test data
        self.db.add_sample('hello', 'en', '/tmp/hello.wav', category='greetings')
        self.db.add_sample('help', 'en', '/tmp/help.wav', category='common')
        self.db.add_sample('house', 'en', '/tmp/house.wav', category='nouns')
        
        # Search by partial word match
        results = self.db.search_samples('hel')
        self.assertGreaterEqual(len(results), 2)  # Should find hello and help
        
        # Search by category
        results = self.db.search_samples('greet')
        self.assertGreaterEqual(len(results), 1)
    
    def test_delete_sample(self):
        """Test sample deletion."""
        # Add sample
        sample_id = self.db.add_sample('test', 'en', '/tmp/test.wav', 'test')
        
        # Verify it exists
        samples = self.db.get_samples(word='test')
        self.assertEqual(len(samples), 1)
        
        # Delete sample
        success = self.db.delete_sample(sample_id)
        self.assertTrue(success)
        
        # Verify it's gone
        samples = self.db.get_samples(word='test')
        self.assertEqual(len(samples), 0)
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        # Add test data
        self.db.add_sample('hello', 'en', '/tmp/hello.wav', category='greetings')
        self.db.add_sample('hola', 'es', '/tmp/hola.wav', category='greetings')
        self.db.add_user_recording('hello', 'en', '/tmp/rec1.wav')
        self.db.add_user_recording('hello', 'en', '/tmp/rec2.wav')
        
        # Get statistics
        stats = self.db.get_statistics()
        
        # Verify statistics
        self.assertEqual(stats['total_samples'], 2)
        self.assertEqual(stats['total_recordings'], 2)
        self.assertIn('en', stats['languages'])
        self.assertIn('es', stats['languages'])
        self.assertIn('greetings', stats['categories'])
    
    def test_add_category(self):
        """Test adding categories."""
        cat_id1 = self.db.add_category('greetings', 'Common greetings')
        self.assertGreater(cat_id1, 0)
        
        # Adding same category again should return existing ID
        cat_id2 = self.db.add_category('greetings', 'Common greetings')
        self.assertEqual(cat_id1, cat_id2)
    
    def test_metadata_handling(self):
        """Test metadata storage and retrieval."""
        metadata = {
            'accent': 'british',
            'gender': 'female',
            'age_range': '30-40',
            'recording_quality': 'high'
        }
        
        sample_id = self.db.add_sample(
            'test', 'en', '/tmp/test.wav', 'test',
            metadata=metadata
        )
        
        # Retrieve and verify metadata
        samples = self.db.get_samples(word='test')
        retrieved_metadata = samples[0]['metadata']
        
        self.assertEqual(retrieved_metadata['accent'], 'british')
        self.assertEqual(retrieved_metadata['gender'], 'female')
        self.assertEqual(retrieved_metadata['recording_quality'], 'high')


class TestDatabaseConcurrency(unittest.TestCase):
    """Test database handles multiple operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_multiple_samples_same_word(self):
        """Test storing multiple samples for same word."""
        # Add multiple samples for 'hello'
        id1 = self.db.add_sample('hello', 'en', '/tmp/hello1.wav',
                                speaker='speaker1')
        id2 = self.db.add_sample('hello', 'en', '/tmp/hello2.wav',
                                speaker='speaker2')
        id3 = self.db.add_sample('hello', 'en', '/tmp/hello3.wav',
                                speaker='speaker3')
        
        # All should have different IDs
        self.assertNotEqual(id1, id2)
        self.assertNotEqual(id2, id3)
        self.assertNotEqual(id1, id3)
        
        # All should be retrievable
        samples = self.db.get_samples(word='hello')
        self.assertEqual(len(samples), 3)
    
    def test_practice_history_multiple_words(self):
        """Test practice history for multiple words."""
        # Practice different words
        words = ['hello', 'goodbye', 'thanks', 'sorry', 'please']
        
        for word in words:
            for i in range(3):  # 3 attempts each
                self.db.add_user_recording(
                    word, 'en', f'/tmp/{word}_{i}.wav',
                    similarity_score=70.0 + i * 5
                )
        
        # Get full history
        history = self.db.get_practice_history()
        self.assertEqual(len(history), len(words))
        
        # Each word should have 3 attempts
        for entry in history:
            self.assertEqual(entry['attempts'], 3)


if __name__ == '__main__':
    unittest.main()
