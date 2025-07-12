#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import csv
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from playwright.async_api import Page, Download

from utils.file_naming import FileNaming

logger = logging.getLogger(__name__)


class FileService:
    """Centralized service for all file I/O operations"""
    
    def __init__(self, base_dir: str = "/data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def read_csv(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Read CSV file and return as DataFrame"""
        try:
            logger.info(f"Reading CSV file: {file_path}")
            return pd.read_csv(file_path)
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {e}")
            raise
    
    def write_csv(self, data: Union[pd.DataFrame, List[Dict]], file_path: Union[str, Path]) -> None:
        """Write data to CSV file"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(data, pd.DataFrame):
                data.to_csv(file_path, index=False)
            else:
                # Write list of dicts
                if data:
                    keys = data[0].keys()
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=keys)
                        writer.writeheader()
                        writer.writerows(data)
            
            logger.info(f"CSV file written: {file_path}")
            
        except Exception as e:
            logger.error(f"Error writing CSV file {file_path}: {e}")
            raise
    
    def read_json(self, file_path: Union[str, Path]) -> Any:
        """Read JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
            raise
    
    def write_json(self, data: Any, file_path: Union[str, Path]) -> None:
        """Write data to JSON file"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"JSON file written: {file_path}")
            
        except Exception as e:
            logger.error(f"Error writing JSON file {file_path}: {e}")
            raise
    
    def read_text(self, file_path: Union[str, Path]) -> str:
        """Read text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            raise
    
    def write_text(self, content: str, file_path: Union[str, Path]) -> None:
        """Write text to file"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Text file written: {file_path}")
            
        except Exception as e:
            logger.error(f"Error writing text file {file_path}: {e}")
            raise
    
    
    def create_directory(self, dir_path: Union[str, Path]) -> Path:
        """Create directory if it doesn't exist"""
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def list_files(self, dir_path: Union[str, Path], pattern: str = "*") -> List[Path]:
        """List files in directory matching pattern"""
        dir_path = Path(dir_path)
        if not dir_path.exists():
            return []
        return list(dir_path.glob(pattern))
    
    def delete_file(self, file_path: Union[str, Path]) -> bool:
        """Delete a file"""
        try:
            file_path = Path(file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def move_file(self, src: Union[str, Path], dst: Union[str, Path]) -> Path:
        """Move a file from source to destination"""
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            
            # Create destination directory if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            final_path = shutil.move(str(src_path), str(dst_path))
            logger.info(f"File moved from {src_path} to {final_path}")
            
            return Path(final_path)
            
        except Exception as e:
            logger.error(f"Error moving file from {src} to {dst}: {e}")
            raise
    
    def copy_file(self, src: Union[str, Path], dst: Union[str, Path]) -> Path:
        """Copy a file from source to destination"""
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            
            # Create destination directory if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            final_path = shutil.copy2(str(src_path), str(dst_path))
            logger.info(f"File copied from {src_path} to {final_path}")
            
            return Path(final_path)
            
        except Exception as e:
            logger.error(f"Error copying file from {src} to {dst}: {e}")
            raise
    
    def get_file_size(self, file_path: Union[str, Path]) -> int:
        """Get file size in bytes"""
        file_path = Path(file_path)
        return file_path.stat().st_size if file_path.exists() else 0
    
    def file_exists(self, file_path: Union[str, Path]) -> bool:
        """Check if file exists"""
        return Path(file_path).exists()
    
    async def download_file(self, download: Download, destination: Union[str, Path]) -> Path:
        """Handle Playwright download and save to destination"""
        try:
            dest_path = Path(destination)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the download
            await download.save_as(str(dest_path))
            logger.info(f"File downloaded to: {dest_path}")
            
            return dest_path
            
        except Exception as e:
            logger.error(f"Error downloading file to {destination}: {e}")
            raise
    
    async def take_screenshot(self, page: Page, name: str, stage: str = "debug") -> Path:
        """Take screenshot with consistent naming"""
        try:
            filename = FileNaming.get_njss_screenshot_name(stage)
            screenshot_path = self.base_dir / "screenshots" / filename
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            
            await page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            raise
    
    def get_case_document_path(self, case_id: str, doc_name: str, doc_type: str) -> Path:
        """Get standardized path for case documents"""
        relative_path = FileNaming.get_case_document_path(case_id, doc_name, doc_type)
        return self.base_dir / "documents" / relative_path
    
    def get_concat_file_path(self, case_id: str) -> Path:
        """Get path for concatenated text file"""
        filename = FileNaming.get_concat_filename(case_id)
        return self.base_dir / "concatenated" / filename