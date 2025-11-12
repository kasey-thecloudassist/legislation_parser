# UK Legislation Parser

A flexible Python parser for UK legislation XML files from legislation.gov.uk. This tool provides multiple chunking strategies for experimenting with different ways to process and structure large legislation documents.

## Features

- **Memory-efficient streaming parser** - Uses `lxml.etree.iterparse()` to handle large XML files without loading everything into memory
- **Multiple chunking strategies** - Experiment with different granularity levels
- **Metadata extraction** - Captures IDs, URIs, dates, numbers, and amendment tracking
- **Hierarchy preservation** - Maintains nested structures (P1→P2→P3→P4)
- **JSON output** - Easy to inspect and load into databases
- **Command-line interface** - Simple CLI for quick experimentation

## Installation

### Using Conda (Recommended)

```bash
# Create and activate the conda environment
conda create -n legislation_parser python=3.11 -y
conda activate legislation_parser

# Install dependencies
pip install -r requirements.txt
```

### Using pip

```bash
pip install lxml>=6.0.0
```

## Usage

### Basic Usage

```bash
# Parse by individual regulations (default)
python legislation_parser.py 1999_3312.txt --output regulations.json

# Parse with pretty-printed JSON
python legislation_parser.py 1999_3312.txt --output regulations.json --pretty

# Extract document metadata
python legislation_parser.py 1999_3312.txt --strategy metadata
```

### Chunking Strategies

The parser supports multiple chunking strategies to experiment with different granularities:

#### 1. **regulation** (Default)
Chunks by individual regulations (P1 elements in the Body section).

```bash
python legislation_parser.py 1999_3312.txt --strategy regulation --output regulations.json
```

**Use case:** Best for treating each regulation as a separate searchable unit. Good for RAG/search systems where users search by regulation number.

**Example output:**
```json
[
  {
    "type": "regulation",
    "number": "1",
    "text": "These Regulations may be cited as...",
    "metadata": {
      "id": "regulation-1",
      "document_uri": "http://www.legislation.gov.uk/...",
      "effective_date": "1999-12-15"
    },
    "has_amendments": false,
    "hierarchy": {
      "sub_sections": []
    }
  }
]
```

#### 2. **regulation_group**
Chunks by regulation groups (P1group elements) which contain related regulations with titles.

```bash
python legislation_parser.py 1999_3312.txt --strategy regulation_group --output groups.json
```

**Use case:** Groups related regulations together under themed sections. Good for topical organization.

#### 3. **part**
Chunks by major Parts (e.g., Part I, Part II).

```bash
python legislation_parser.py 1999_3312.txt --strategy part --output parts.json
```

**Use case:** Highest level chunking. Good for broad categorization or when Parts represent distinct topics.

#### 4. **schedule**
Chunks by Schedules (supporting documents attached to the main legislation).

```bash
python legislation_parser.py 1999_3312.txt --strategy schedule --output schedules.json
```

**Use case:** Schedules often contain detailed forms, procedures, or supplementary rules. Useful when schedules should be searchable separately.

#### 5. **paragraph**
Chunks by paragraphs within schedules (P1 elements inside Schedule sections).

```bash
python legislation_parser.py 1999_3312.txt --strategy paragraph --output schedule_paragraphs.json
```

**Use case:** Finest granularity for schedule content. Good for detailed schedule analysis.

#### 6. **all**
Extracts all chunk types and returns them organized by type.

```bash
python legislation_parser.py 1999_3312.txt --strategy all --output all_chunks.json
```

**Use case:** Best for initial exploration to see all structural elements and decide on chunking strategy.

**Example output:**
```json
{
  "parts": [...],
  "regulations": [...],
  "regulation_groups": [...],
  "schedules": [...],
  "paragraphs": [...]
}
```

#### 7. **metadata**
Extracts only document-level metadata (title, year, number, dates, statistics).

```bash
python legislation_parser.py 1999_3312.txt --strategy metadata
```

**Example output:**
```json
{
  "title": "The Maternity and Parental Leave etc. Regulations 1999",
  "year": "1999",
  "number": "3312",
  "made_date": "1999-12-10",
  "total_paragraphs": 38,
  "body_paragraphs": 25,
  "schedule_paragraphs": 13
}
```

## Chunk Structure

All chunks (except metadata) follow this structure:

```json
{
  "type": "regulation|part|schedule|paragraph|regulation_group",
  "number": "1",  // Regulation/paragraph number
  "title": "Optional title for groups/schedules",
  "text": "Full text content with nested elements combined",
  "metadata": {
    "id": "regulation-1",
    "document_uri": "http://www.legislation.gov.uk/...",
    "id_uri": "http://www.legislation.gov.uk/...",
    "effective_date": "1999-12-15"  // When this version became effective
  },
  "has_amendments": true,  // Whether this contains tracked changes
  "hierarchy": {
    "sub_sections": [
      {
        "level": "P2",  // P2, P3, or P4
        "number": "1",
        "text": "Sub-section text",
        "metadata": {...}
      }
    ]
  }
}
```

## Experimenting with Chunking Strategies

Here's a suggested workflow for finding the best chunking strategy for your database:

### Step 1: Explore the Document Structure
```bash
# Get document metadata
python legislation_parser.py 1999_3312.txt --strategy metadata

# Extract all chunk types to see everything
python legislation_parser.py 1999_3312.txt --strategy all --output exploration.json --pretty
```

### Step 2: Try Different Granularities
```bash
# Coarse granularity (fewer, larger chunks)
python legislation_parser.py 1999_3312.txt --strategy part --output parts.json --pretty

# Medium granularity (most common)
python legislation_parser.py 1999_3312.txt --strategy regulation --output regulations.json --pretty

# Fine granularity (many small chunks)
python legislation_parser.py 1999_3312.txt --strategy paragraph --output paragraphs.json --pretty
```

### Step 3: Analyze Chunk Sizes
```python
import json

# Load your chunks
with open('regulations.json') as f:
    chunks = json.load(f)

# Analyze chunk sizes
for chunk in chunks:
    text_length = len(chunk.get('text', ''))
    print(f"Regulation {chunk.get('number')}: {text_length} characters")
```

### Step 4: Consider Your Use Case

- **For search/RAG systems:** `regulation` or `regulation_group` work well - users typically search by regulation number
- **For semantic similarity:** Smaller chunks (`paragraph` or `regulation`) capture more specific concepts
- **For context preservation:** Larger chunks (`part` or `regulation_group`) maintain more context
- **For hybrid approaches:** Use `all` strategy and create multiple chunk sizes for different search strategies

## UK Legislation XML Structure

This parser is designed for the standard UK legislation.gov.uk XML format, which follows this hierarchy:

```
Legislation
├── Metadata (document info, dates, amendment history)
└── Secondary
    ├── SecondaryPrelims (title, number, dates)
    ├── Body
    │   └── Part (multiple)
    │       └── P1group (regulation groups)
    │           └── P1 (individual regulations)
    │               ├── Pnumber
    │               └── P1para
    │                   ├── P2 (sub-sections)
    │                   │   └── P3
    │                   │       └── P4
    │                   └── Text, Lists, etc.
    └── Schedules
        └── Schedule (multiple)
            └── P1 (paragraphs)
                └── P3, P4...
```

## Key Features Explained

### Memory Efficiency
The parser uses streaming (`iterparse`) to process XML incrementally, clearing elements from memory as it goes. This allows it to handle very large legislation files (10,000+ lines) without memory issues.

### Amendment Tracking
The parser detects `<Addition>` and `<Substitution>` elements in the XML, which track legislative amendments. The `has_amendments` flag indicates whether a chunk contains tracked changes.

### Hierarchy Extraction
For regulations and paragraphs, the parser extracts nested structures (P2, P3, P4 sub-sections) into a `hierarchy` field. This preserves the regulatory structure for display or analysis.

### URI Preservation
Each element has unique `document_uri` and `id_uri` attributes that serve as stable identifiers. These are preserved in the metadata for linking and referencing.

## Advanced Usage

### Using as a Library

```python
from legislation_parser import LegislationParser

# Initialize parser
parser = LegislationParser('1999_3312.txt')

# Get metadata
metadata = parser.get_document_metadata()
print(f"Title: {metadata['title']}")

# Parse regulations
regulations = parser.parse_by_regulation()
for reg in regulations:
    print(f"Regulation {reg['number']}: {reg['text'][:100]}...")

# Parse everything
all_chunks = parser.parse_all()
print(f"Found {len(all_chunks['regulations'])} regulations")
print(f"Found {len(all_chunks['schedules'])} schedules")
```

### Custom Processing

```python
from legislation_parser import LegislationParser
import json

parser = LegislationParser('1999_3312.txt')

# Filter only amended regulations
regulations = parser.parse_by_regulation()
amended = [r for r in regulations if r['has_amendments']]

# Save to database (pseudo-code)
for reg in regulations:
    db.insert({
        'doc_id': reg['metadata']['id'],
        'number': reg['number'],
        'text': reg['text'],
        'effective_date': reg['metadata'].get('effective_date'),
        'embedding': create_embedding(reg['text'])
    })
```

## Troubleshooting

### File Not Found
Ensure you're providing the correct path to the XML file:
```bash
python legislation_parser.py /full/path/to/1999_3312.txt
```

### Memory Issues
If you encounter memory issues with very large files, use smaller chunk strategies:
```bash
# Use regulation instead of part for smaller chunks
python legislation_parser.py large_file.txt --strategy regulation
```

### Empty Output
Check that the XML file is valid and follows the legislation.gov.uk format. Try the metadata strategy first:
```bash
python legislation_parser.py your_file.txt --strategy metadata
```

## Next Steps

Once you've experimented with chunking strategies and chosen one that fits your needs:

1. **Database Design:** Design your schema based on the chunk structure
2. **Embedding Generation:** Generate embeddings for the text field of each chunk
3. **Indexing:** Create appropriate indexes on regulation numbers, dates, and IDs
4. **Search Implementation:** Build search functionality using the structured chunks

## License

This project is provided as-is for educational and research purposes.
