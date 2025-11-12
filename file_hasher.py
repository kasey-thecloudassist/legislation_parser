import hashlib
import os
import json
import sys

class FileHasher:
    def __init__(self, file_path, algorithm="sha256", storage_file="hash_store.json"):
        self.file_path = file_path
        self.algorithm = algorithm
        self.storage_file = storage_file
        self.hashes = self._load_hashes()

    def compute_hash(self):
        """Compute the hash of the hardcoded file."""
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")

        hasher = hashlib.new(self.algorithm)
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def save_hash(self):
        """Save the computed hash to storage."""
        file_hash = self.compute_hash()
        self.hashes[self.file_path] = file_hash
        self._save_hashes()
        print(f"Hash saved: {file_hash}")

    def compare_hash(self):
        """Compare current file hash with stored hash."""
        current_hash = self.compute_hash()
        stored_hash = self.hashes.get(self.file_path)
        if stored_hash:
            if current_hash == stored_hash:
                print("✅ Hash matches the stored hash.")
            else:
                print("❌ Hash does NOT match the stored hash.")
        else:
            print("No stored hash found for this file.")

    def _save_hashes(self):
        with open(self.storage_file, "w") as f:
            json.dump(self.hashes, f)

    def _load_hashes(self):
        if os.path.exists(self.storage_file):
            with open(self.storage_file, "r") as f:
                return json.load(f)
        return {}

if __name__ == "__main__":
    # Hardcoded file path
    FILE_PATH = "1999_3312.txt"  # Change this to your file
    hasher = FileHasher(FILE_PATH)

    # Check command-line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "save":
            hasher.save_hash()
        elif command == "compare":
            hasher.compare_hash()
        else:
            print("Unknown command. Use 'save' or 'compare'.")
    else:
        # No param: just print the hash
        print(f"Computed hash: {hasher.compute_hash()}")