#!/usr/bin/env python3
"""
PDF Text Extraction Script
Extracts text from all PDFs in current directory and saves as markdown files.
Preserves tables as markdown tables where possible.
"""

import os
import sys
import subprocess
import fitz  # PyMuPDF
import re
from pathlib import Path

def install_requirements():
    """Install required dependencies if not available"""
    try:
        import fitz
        print("✓ PyMuPDF already installed")
    except ImportError:
        print("Installing PyMuPDF...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF"])
        import fitz
        print("✓ PyMuPDF installed successfully")

def clean_text(text):
    """Clean extracted text for better markdown formatting"""
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    # Fix common formatting issues
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between lowercase and uppercase
    text = re.sub(r'\s+', ' ', text)  # Normalize spaces
    text = text.strip()
    return text

def extract_tables_from_page(page):
    """Extract tables from a page and convert to markdown"""
    tables = []
    try:
        # Find tables on the page
        page_tables = page.find_tables()
        for table in page_tables:
            table_data = table.extract()
            if table_data and len(table_data) > 0:
                # Convert to markdown table
                md_table = []
                
                # Header row
                if len(table_data) > 0:
                    header = [str(cell) if cell else "" for cell in table_data[0]]
                    md_table.append("| " + " | ".join(header) + " |")
                    md_table.append("| " + " | ".join(["---"] * len(header)) + " |")
                
                # Data rows
                for row in table_data[1:]:
                    row_data = [str(cell) if cell else "" for cell in row]
                    md_table.append("| " + " | ".join(row_data) + " |")
                
                if md_table:
                    tables.append("\n".join(md_table))
    
    except Exception as e:
        print(f"  Warning: Could not extract tables - {e}")
    
    return tables

def extract_pdf_to_markdown(pdf_path):
    """Extract text and tables from PDF and format as markdown"""
    print(f"Processing: {os.path.basename(pdf_path)}")
    
    try:
        doc = fitz.open(pdf_path)
        content = []
        
        # Add document title
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        content.append(f"# {pdf_name.replace('_', ' ').replace('-', ' ').title()}")
        content.append("")
        content.append(f"*Extracted from: {os.path.basename(pdf_path)}*")
        content.append("")
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Add page header for multi-page documents
            if len(doc) > 1:
                content.append(f"## Page {page_num + 1}")
                content.append("")
            
            # Extract tables first
            tables = extract_tables_from_page(page)
            
            # Extract text
            text = page.get_text()
            cleaned_text = clean_text(text)
            
            if cleaned_text:
                content.append(cleaned_text)
                content.append("")
            
            # Add tables
            for table in tables:
                content.append(table)
                content.append("")
        
        doc.close()
        
        # Join all content
        markdown_content = "\n".join(content)
        
        # Save as markdown file
        md_filename = os.path.splitext(pdf_path)[0] + ".md"
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"  ✓ Saved: {os.path.basename(md_filename)}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error processing {pdf_path}: {e}")
        return False

def main():
    """Main execution function"""
    print("PDF to Markdown Extractor")
    print("=" * 40)
    
    # Install dependencies
    install_requirements()
    
    # Get current directory
    current_dir = Path.cwd()
    print(f"Working directory: {current_dir}")
    
    # Find all PDF files
    pdf_files = list(current_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in current directory")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    print()
    
    # Process each PDF
    success_count = 0
    for pdf_file in pdf_files:
        if extract_pdf_to_markdown(str(pdf_file)):
            success_count += 1
    
    print()
    print(f"✓ Successfully processed {success_count}/{len(pdf_files)} PDF files")
    
    # List generated markdown files
    md_files = list(current_dir.glob("*.md"))
    if md_files:
        print("\nGenerated markdown files:")
        for md_file in sorted(md_files):
            print(f"  - {md_file.name}")

if __name__ == "__main__":
    main()