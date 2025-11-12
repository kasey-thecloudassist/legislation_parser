#!/usr/bin/env python3
"""
Legislation Parser - Flexible XML Chunking for UK Legislation

This script provides multiple chunking strategies for parsing large UK legislation XML files
from legislation.gov.uk. It uses streaming parsing to handle large files efficiently.

Chunking Strategies:
- 'part': Chunk by Parts (e.g., Part I, Part II)
- 'regulation': Chunk by individual Regulations (P1 elements in Body)
- 'regulation_group': Chunk by regulation groups (P1group elements)
- 'schedule': Chunk by Schedules
- 'paragraph': Chunk by paragraphs within schedules
- 'all': Extract all types with their hierarchy
"""

import json
import argparse
import io
from pathlib import Path
from typing import Dict, List, Any, Optional
from lxml import etree


class LegislationParser:
    """Parser for UK legislation XML files with flexible chunking strategies."""

    # Namespace for legislation.gov.uk XML
    NAMESPACES = {
        'leg': 'http://www.legislation.gov.uk/namespaces/legislation',
        'ukm': 'http://www.legislation.gov.uk/namespaces/metadata',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dct': 'http://purl.org/dc/terms/',
    }

    def __init__(self, xml_file: str):
        """Initialize parser with XML file path."""
        self.xml_file = Path(xml_file)
        if not self.xml_file.exists():
            raise FileNotFoundError(f"XML file not found: {xml_file}")

        # Check if file starts with non-XML text and needs preprocessing
        self._needs_skip_first_line = False
        with open(self.xml_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line and not first_line.startswith('<?xml') and not first_line.startswith('<'):
                self._needs_skip_first_line = True

    def _get_xml_source(self):
        """Get XML source, skipping first line if needed."""
        if self._needs_skip_first_line:
            # Read file and skip first line
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[1:]  # Skip first line
                xml_content = ''.join(lines)
                return io.BytesIO(xml_content.encode('utf-8'))
        else:
            return str(self.xml_file)

    def _extract_text(self, element) -> str:
        """Extract all text content from an element, including nested elements."""
        texts = []

        # Get text from this element
        if element.text:
            texts.append(element.text.strip())

        # Get text from all children recursively
        for child in element:
            child_text = self._extract_text(child)
            if child_text:
                texts.append(child_text)

            # Get tail text (text after the child element)
            if child.tail:
                tail = child.tail.strip()
                if tail:
                    texts.append(tail)

        return ' '.join(texts)

    def _extract_metadata(self, element) -> Dict[str, Any]:
        """Extract common metadata attributes from an element."""
        metadata = {}

        # Extract attributes
        if 'id' in element.attrib:
            metadata['id'] = element.attrib['id']
        if 'DocumentURI' in element.attrib:
            metadata['document_uri'] = element.attrib['DocumentURI']
        if 'IdURI' in element.attrib:
            metadata['id_uri'] = element.attrib['IdURI']
        if 'RestrictStartDate' in element.attrib:
            metadata['effective_date'] = element.attrib['RestrictStartDate']

        return metadata

    def _extract_number(self, element) -> Optional[str]:
        """Extract number from Pnumber or Number element."""
        # Look for Pnumber child
        pnumber = element.find('.//leg:Pnumber', self.NAMESPACES)
        if pnumber is not None and pnumber.text:
            return pnumber.text.strip()

        # Look for Number child
        number = element.find('.//leg:Number', self.NAMESPACES)
        if number is not None and number.text:
            return number.text.strip()

        return None

    def _extract_title(self, element) -> Optional[str]:
        """Extract title from Title or TitleBlock element."""
        # Try TitleBlock > Title first (for schedules)
        title_block = element.find('.//leg:TitleBlock/leg:Title', self.NAMESPACES)
        if title_block is not None:
            return self._extract_text(title_block)

        # Try direct Title
        title = element.find('.//leg:Title', self.NAMESPACES)
        if title is not None:
            return self._extract_text(title)

        return None

    def _has_amendments(self, element) -> bool:
        """Check if element contains amendment markup (Addition/Substitution)."""
        additions = element.findall('.//leg:Addition', self.NAMESPACES)
        substitutions = element.findall('.//leg:Substitution', self.NAMESPACES)
        return len(additions) > 0 or len(substitutions) > 0

    def _build_chunk(self, element, chunk_type: str) -> Dict[str, Any]:
        """Build a standardized chunk dictionary from an element."""
        chunk = {
            'type': chunk_type,
            'metadata': self._extract_metadata(element),
        }

        # Extract number
        number = self._extract_number(element)
        if number:
            chunk['number'] = number

        # Extract title
        title = self._extract_title(element)
        if title:
            chunk['title'] = title

        # Extract text content
        text = self._extract_text(element)
        if text:
            chunk['text'] = text

        # Check for amendments
        chunk['has_amendments'] = self._has_amendments(element)

        # Extract hierarchy information for nested structures
        if chunk_type in ['regulation', 'paragraph']:
            chunk['hierarchy'] = self._extract_hierarchy(element)

        return chunk

    def _extract_hierarchy(self, element) -> Dict[str, List[Dict]]:
        """Extract nested hierarchy (P2, P3, P4 elements)."""
        hierarchy = {}

        # Find nested P2 elements
        p2_elements = element.findall('.//leg:P2', self.NAMESPACES)
        if p2_elements:
            hierarchy['sub_sections'] = []
            for p2 in p2_elements:
                sub = {
                    'level': 'P2',
                    'number': self._extract_number(p2),
                    'text': self._extract_text(p2),
                    'metadata': self._extract_metadata(p2)
                }
                hierarchy['sub_sections'].append(sub)

        # Find nested P3 elements
        p3_elements = element.findall('.//leg:P3', self.NAMESPACES)
        if p3_elements:
            if 'sub_sections' not in hierarchy:
                hierarchy['sub_sections'] = []
            for p3 in p3_elements:
                sub = {
                    'level': 'P3',
                    'number': self._extract_number(p3),
                    'text': self._extract_text(p3),
                    'metadata': self._extract_metadata(p3)
                }
                hierarchy['sub_sections'].append(sub)

        return hierarchy

    def parse_by_part(self) -> List[Dict[str, Any]]:
        """Parse and chunk by Parts (e.g., Part I, Part II)."""
        chunks = []

        xml_source = self._get_xml_source()
        context = etree.iterparse(xml_source, events=('end',), tag='{http://www.legislation.gov.uk/namespaces/legislation}Part')

        for event, element in context:
            chunk = self._build_chunk(element, 'part')
            chunks.append(chunk)

            # Clear element to free memory
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]

        return chunks

    def parse_by_regulation(self) -> List[Dict[str, Any]]:
        """Parse and chunk by individual Regulations (P1 elements in Body)."""
        chunks = []

        xml_source = self._get_xml_source()
        context = etree.iterparse(xml_source, events=('end',), tag='{http://www.legislation.gov.uk/namespaces/legislation}P1')

        for event, element in context:
            # Check if this P1 is in the Body (not in Schedule)
            parent = element.getparent()
            while parent is not None:
                if parent.tag == '{http://www.legislation.gov.uk/namespaces/legislation}Body':
                    chunk = self._build_chunk(element, 'regulation')
                    chunks.append(chunk)
                    break
                elif parent.tag == '{http://www.legislation.gov.uk/namespaces/legislation}Schedule':
                    # This P1 is in a schedule, skip it
                    break
                parent = parent.getparent()

            # Clear element to free memory
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]

        return chunks

    def parse_by_regulation_group(self) -> List[Dict[str, Any]]:
        """Parse and chunk by regulation groups (P1group elements)."""
        chunks = []

        xml_source = self._get_xml_source()
        context = etree.iterparse(xml_source, events=('end',), tag='{http://www.legislation.gov.uk/namespaces/legislation}P1group')

        for event, element in context:
            chunk = self._build_chunk(element, 'regulation_group')
            chunks.append(chunk)

            # Clear element to free memory
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]

        return chunks

    def parse_by_schedule(self) -> List[Dict[str, Any]]:
        """Parse and chunk by Schedules."""
        chunks = []

        xml_source = self._get_xml_source()
        context = etree.iterparse(xml_source, events=('end',), tag='{http://www.legislation.gov.uk/namespaces/legislation}Schedule')

        for event, element in context:
            chunk = self._build_chunk(element, 'schedule')
            chunks.append(chunk)

            # Clear element to free memory
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]

        return chunks

    def parse_by_paragraph(self) -> List[Dict[str, Any]]:
        """Parse and chunk by paragraphs within schedules (P1 in schedules)."""
        chunks = []

        xml_source = self._get_xml_source()
        context = etree.iterparse(xml_source, events=('end',), tag='{http://www.legislation.gov.uk/namespaces/legislation}P1')

        for event, element in context:
            # Check if this P1 is in a Schedule (not in Body)
            parent = element.getparent()
            while parent is not None:
                if parent.tag == '{http://www.legislation.gov.uk/namespaces/legislation}Schedule':
                    chunk = self._build_chunk(element, 'paragraph')
                    chunks.append(chunk)
                    break
                elif parent.tag == '{http://www.legislation.gov.uk/namespaces/legislation}Body':
                    # This P1 is in body, skip it
                    break
                parent = parent.getparent()

            # Clear element to free memory
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]

        return chunks

    def parse_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Parse and extract all chunk types with their hierarchies."""
        return {
            'parts': self.parse_by_part(),
            'regulations': self.parse_by_regulation(),
            'regulation_groups': self.parse_by_regulation_group(),
            'schedules': self.parse_by_schedule(),
            'paragraphs': self.parse_by_paragraph(),
        }

    def get_document_metadata(self) -> Dict[str, Any]:
        """Extract document-level metadata."""
        metadata = {}

        # Parse just the metadata section
        xml_source = self._get_xml_source()
        context = etree.iterparse(xml_source, events=('end',), tag='{http://www.legislation.gov.uk/namespaces/metadata}Metadata')

        for event, element in context:
            # Extract title
            title_elem = element.find('.//dc:title', self.NAMESPACES)
            if title_elem is not None:
                metadata['title'] = title_elem.text

            # Extract year and number
            year_elem = element.find('.//ukm:Year', self.NAMESPACES)
            if year_elem is not None and 'Value' in year_elem.attrib:
                metadata['year'] = year_elem.attrib['Value']

            number_elem = element.find('.//ukm:Number', self.NAMESPACES)
            if number_elem is not None and 'Value' in number_elem.attrib:
                metadata['number'] = number_elem.attrib['Value']

            # Extract dates
            made_elem = element.find('.//ukm:Made', self.NAMESPACES)
            if made_elem is not None and 'Date' in made_elem.attrib:
                metadata['made_date'] = made_elem.attrib['Date']

            # Extract statistics
            total_paras = element.find('.//ukm:TotalParagraphs', self.NAMESPACES)
            if total_paras is not None and 'Value' in total_paras.attrib:
                metadata['total_paragraphs'] = int(total_paras.attrib['Value'])

            body_paras = element.find('.//ukm:BodyParagraphs', self.NAMESPACES)
            if body_paras is not None and 'Value' in body_paras.attrib:
                metadata['body_paragraphs'] = int(body_paras.attrib['Value'])

            schedule_paras = element.find('.//ukm:ScheduleParagraphs', self.NAMESPACES)
            if schedule_paras is not None and 'Value' in schedule_paras.attrib:
                metadata['schedule_paragraphs'] = int(schedule_paras.attrib['Value'])

            break

        return metadata


def main():
    """Command-line interface for the legislation parser."""
    parser = argparse.ArgumentParser(
        description='Parse UK legislation XML files with flexible chunking strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Chunking strategies:
  part              - Chunk by Parts (e.g., Part I, Part II)
  regulation        - Chunk by individual Regulations (P1 elements in Body)
  regulation_group  - Chunk by regulation groups (P1group elements)
  schedule          - Chunk by Schedules
  paragraph         - Chunk by paragraphs within schedules
  all               - Extract all types with their hierarchy
  metadata          - Extract document metadata only

Examples:
  # Parse by individual regulations
  python legislation_parser.py 1999_3312.txt --strategy regulation --output regulations.json

  # Extract document metadata
  python legislation_parser.py 1999_3312.txt --strategy metadata

  # Extract all chunk types
  python legislation_parser.py 1999_3312.txt --strategy all --output all_chunks.json
        """
    )

    parser.add_argument('xml_file', help='Path to the legislation XML file')
    parser.add_argument(
        '--strategy',
        choices=['part', 'regulation', 'regulation_group', 'schedule', 'paragraph', 'all', 'metadata'],
        default='regulation',
        help='Chunking strategy (default: regulation)'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Output JSON file (default: print to stdout)'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output'
    )

    args = parser.parse_args()

    # Initialize parser
    leg_parser = LegislationParser(args.xml_file)

    # Parse based on strategy
    if args.strategy == 'metadata':
        result = leg_parser.get_document_metadata()
    elif args.strategy == 'part':
        result = leg_parser.parse_by_part()
    elif args.strategy == 'regulation':
        result = leg_parser.parse_by_regulation()
    elif args.strategy == 'regulation_group':
        result = leg_parser.parse_by_regulation_group()
    elif args.strategy == 'schedule':
        result = leg_parser.parse_by_schedule()
    elif args.strategy == 'paragraph':
        result = leg_parser.parse_by_paragraph()
    elif args.strategy == 'all':
        result = leg_parser.parse_all()

    # Format output
    indent = 2 if args.pretty else None
    json_output = json.dumps(result, indent=indent, ensure_ascii=False)

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json_output, encoding='utf-8')
        print(f"Output written to {args.output}")

        # Print summary
        if args.strategy == 'metadata':
            print(f"\nDocument: {result.get('title', 'Unknown')}")
            print(f"Year: {result.get('year', 'Unknown')}, Number: {result.get('number', 'Unknown')}")
        elif args.strategy == 'all':
            print(f"\nExtracted chunks:")
            for chunk_type, chunks in result.items():
                print(f"  {chunk_type}: {len(chunks)} items")
        else:
            print(f"\nExtracted {len(result)} {args.strategy} chunks")
    else:
        print(json_output)


if __name__ == '__main__':
    main()
