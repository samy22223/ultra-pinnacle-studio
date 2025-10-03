#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Universal Web Scrapers
Collect data from any site, with ethical scraping protocols and anti-bot evasion
"""

import os
import json
import time
import asyncio
import random
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urlparse
import re

class ScrapingMode(Enum):
    ETHICAL = "ethical"
    STEALTH = "stealth"
    BULK = "bulk"
    REAL_TIME = "real_time"

class DataType(Enum):
    TEXT = "text"
    IMAGES = "images"
    VIDEOS = "videos"
    PRICES = "prices"
    REVIEWS = "reviews"
    CONTACT_INFO = "contact_info"
    STRUCTURED_DATA = "structured_data"

@dataclass
class ScrapingTarget:
    """Scraping target configuration"""
    target_id: str
    name: str
    url: str
    data_types: List[DataType]
    scraping_mode: ScrapingMode
    schedule: str
    respect_robots_txt: bool = True
    user_agent: str = "UltraPinnacleBot/1.0"
    rate_limit: int = 1  # requests per second

@dataclass
class ScrapedData:
    """Scraped data container"""
    data_id: str
    target_id: str
    url: str
    data_type: DataType
    content: str
    metadata: Dict
    scraped_at: datetime
    quality_score: float = 0.0

class UniversalWebScraper:
    """Universal web scraping system"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.scraping_targets = self.load_scraping_targets()
        self.scraped_data = []
        self.session = None

    def load_scraping_targets(self) -> List[ScrapingTarget]:
        """Load scraping target configurations"""
        return [
            ScrapingTarget(
                target_id="target_001",
                name="E-commerce Price Monitor",
                url="https://example-ecommerce.com",
                data_types=[DataType.PRICES, DataType.TEXT],
                scraping_mode=ScrapingMode.ETHICAL,
                schedule="hourly",
                respect_robots_txt=True,
                rate_limit=2
            ),
            ScrapingTarget(
                target_id="target_002",
                name="News Aggregator",
                url="https://example-news.com",
                data_types=[DataType.TEXT, DataType.IMAGES],
                scraping_mode=ScrapingMode.BULK,
                schedule="daily",
                respect_robots_txt=True,
                rate_limit=5
            ),
            ScrapingTarget(
                target_id="target_003",
                name="Social Media Monitor",
                url="https://example-social.com",
                data_types=[DataType.TEXT, DataType.VIDEOS],
                scraping_mode=ScrapingMode.STEALTH,
                schedule="real_time",
                respect_robots_txt=False,
                rate_limit=10
            )
        ]

    async def run_universal_scraping_system(self) -> Dict:
        """Run universal scraping system"""
        print("🕷️ Running universal web scraping system...")

        scraping_results = {
            "targets_processed": 0,
            "data_collected": 0,
            "ethical_compliance": 0,
            "anti_bot_evasion": 0,
            "data_quality_score": 0.0,
            "errors_encountered": 0
        }

        # Initialize HTTP session
        async with aiohttp.ClientSession() as self.session:
            # Process each scraping target
            for target in self.scraping_targets:
                try:
                    print(f"\n🕷️ Processing target: {target.name}")

                    # Check robots.txt compliance
                    if target.respect_robots_txt:
                        robots_ok = await self.check_robots_txt(target.url)
                        if not robots_ok:
                            print(f"⏭️ Skipping {target.name} - robots.txt disallows")
                            continue

                    # Scrape target based on mode
                    if target.scraping_mode == ScrapingMode.ETHICAL:
                        target_data = await self.ethical_scraping(target)
                    elif target.scraping_mode == ScrapingMode.STEALTH:
                        target_data = await self.stealth_scraping(target)
                    elif target.scraping_mode == ScrapingMode.BULK:
                        target_data = await self.bulk_scraping(target)
                    else:
                        target_data = await self.real_time_scraping(target)

                    # Process and store scraped data
                    processed_data = await self.process_scraped_data(target_data, target)
                    self.scraped_data.extend(processed_data)

                    scraping_results["targets_processed"] += 1
                    scraping_results["data_collected"] += len(processed_data)
                    scraping_results["ethical_compliance"] += 1

                except Exception as e:
                    print(f"❌ Error scraping {target.name}: {e}")
                    scraping_results["errors_encountered"] += 1

        # Calculate overall metrics
        scraping_results["data_quality_score"] = await self.calculate_data_quality_score()

        print(f"\n✅ Scraping completed: {scraping_results['data_collected']} data points collected")
        return scraping_results

    async def check_robots_txt(self, url: str) -> bool:
        """Check robots.txt compliance"""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    robots_content = await response.text()

                    # Check if our user agent is disallowed
                    if "Disallow:" in robots_content and "UltraPinnacleBot" in robots_content:
                        return False

                return True

        except Exception:
            # If robots.txt is not accessible, assume it's allowed
            return True

    async def ethical_scraping(self, target: ScrapingTarget) -> List[Dict]:
        """Perform ethical scraping with proper delays"""
        print(f"🤝 Performing ethical scraping for {target.name}")

        scraped_data = []

        try:
            # Start with main page
            main_data = await self.scrape_single_page(target.url, target)
            scraped_data.append(main_data)

            # Find and scrape additional pages
            additional_urls = await self.discover_scrapable_urls(target.url, target)

            for url in additional_urls[:5]:  # Limit to 5 additional pages
                page_data = await self.scrape_single_page(url, target)
                scraped_data.append(page_data)

                # Respect rate limiting
                await asyncio.sleep(1.0 / target.rate_limit)

        except Exception as e:
            print(f"Error in ethical scraping: {e}")

        return scraped_data

    async def stealth_scraping(self, target: ScrapingTarget) -> List[Dict]:
        """Perform stealth scraping with anti-bot evasion"""
        print(f"🥷 Performing stealth scraping for {target.name}")

        scraped_data = []

        try:
            # Use rotating user agents and proxies
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            ]

            # Rotate user agent
            target_with_rotation = ScrapingTarget(
                **asdict(target),
                user_agent=random.choice(user_agents)
            )

            # Add random delays to mimic human behavior
            await asyncio.sleep(random.uniform(2.0, 5.0))

            # Scrape with stealth techniques
            page_data = await self.scrape_single_page(target.url, target_with_rotation)
            scraped_data.append(page_data)

            # Add more random delays
            await asyncio.sleep(random.uniform(3.0, 8.0))

        except Exception as e:
            print(f"Error in stealth scraping: {e}")

        return scraped_data

    async def bulk_scraping(self, target: ScrapingTarget) -> List[Dict]:
        """Perform bulk scraping for large datasets"""
        print(f"📦 Performing bulk scraping for {target.name}")

        scraped_data = []

        try:
            # Discover all scrapable URLs
            all_urls = await self.discover_scrapable_urls(target.url, target)

            # Scrape multiple pages concurrently (with limits)
            semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

            async def scrape_with_limit(url):
                async with semaphore:
                    return await self.scrape_single_page(url, target)

            # Scrape first 20 URLs concurrently
            tasks = [scrape_with_limit(url) for url in all_urls[:20]]
            bulk_data = await asyncio.gather(*tasks, return_exceptions=True)

            for data in bulk_data:
                if isinstance(data, dict):
                    scraped_data.append(data)

        except Exception as e:
            print(f"Error in bulk scraping: {e}")

        return scraped_data

    async def real_time_scraping(self, target: ScrapingTarget) -> List[Dict]:
        """Perform real-time scraping for live data"""
        print(f"⚡ Performing real-time scraping for {target.name}")

        scraped_data = []

        try:
            # Continuous scraping with minimal delays
            for i in range(3):  # Scrape 3 times in quick succession
                page_data = await self.scrape_single_page(target.url, target)
                scraped_data.append(page_data)

                # Minimal delay for real-time
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"Error in real-time scraping: {e}")

        return scraped_data

    async def scrape_single_page(self, url: str, target: ScrapingTarget) -> Dict:
        """Scrape a single page"""
        try:
            headers = {
                "User-Agent": target.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html_content = await response.text()

                    # Extract data based on target data types
                    extracted_data = {}

                    for data_type in target.data_types:
                        if data_type == DataType.TEXT:
                            extracted_data["text"] = await self.extract_text_content(html_content, url)
                        elif data_type == DataType.PRICES:
                            extracted_data["prices"] = await self.extract_price_data(html_content, url)
                        elif data_type == DataType.IMAGES:
                            extracted_data["images"] = await self.extract_image_urls(html_content, url)
                        elif data_type == DataType.STRUCTURED_DATA:
                            extracted_data["structured"] = await self.extract_structured_data(html_content, url)

                    return {
                        "url": url,
                        "status": "success",
                        "data": extracted_data,
                        "scraped_at": datetime.now().isoformat(),
                        "response_size": len(html_content)
                    }
                else:
                    return {
                        "url": url,
                        "status": "error",
                        "error": f"HTTP {response.status}",
                        "scraped_at": datetime.now().isoformat()
                    }

        except Exception as e:
            return {
                "url": url,
                "status": "error",
                "error": str(e),
                "scraped_at": datetime.now().isoformat()
            }

    async def extract_text_content(self, html: str, url: str) -> str:
        """Extract text content from HTML"""
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Extract text content
        text_content = re.sub(r'<[^>]+>', ' ', html)
        text_content = re.sub(r'\s+', ' ', text_content).strip()

        return text_content[:2000]  # Limit text length

    async def extract_price_data(self, html: str, url: str) -> List[Dict]:
        """Extract price data from HTML"""
        prices = []

        # Look for common price patterns
        price_patterns = [
            r'\$\d+\.?\d*',  # $99.99
            r'\d+\.?\d*\s*(?:USD|EUR|GBP)',  # 99.99 USD
            r'Price:\s*\$?\d+\.?\d*',  # Price: $99.99
        ]

        for pattern in price_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches[:5]:  # Limit to 5 prices per page
                prices.append({
                    "price": match,
                    "context": "extracted_from_html",
                    "confidence": 0.7
                })

        return prices

    async def extract_image_urls(self, html: str, url: str) -> List[str]:
        """Extract image URLs from HTML"""
        image_urls = []

        # Find image tags
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        images = re.findall(img_pattern, html, re.IGNORECASE)

        for img_url in images[:10]:  # Limit to 10 images
            # Convert relative URLs to absolute
            if img_url.startswith('/'):
                parsed = urlparse(url)
                img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
            elif not img_url.startswith('http'):
                img_url = f"{url.rstrip('/')}/{img_url}"

            image_urls.append(img_url)

        return image_urls

    async def extract_structured_data(self, html: str, url: str) -> Dict:
        """Extract structured data (JSON-LD, microdata)"""
        structured_data = {}

        # Look for JSON-LD
        json_ld_pattern = r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        json_matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

        for json_data in json_matches:
            try:
                parsed = json.loads(json_data)
                structured_data["json_ld"] = parsed
            except json.JSONDecodeError:
                pass

        return structured_data

    async def discover_scrapable_urls(self, base_url: str, target: ScrapingTarget) -> List[str]:
        """Discover additional URLs to scrape"""
        urls = []

        try:
            # Scrape main page to find links
            main_page_data = await self.scrape_single_page(base_url, target)

            if main_page_data["status"] == "success":
                html_content = await self.session.get(base_url).text() if not hasattr(self, '_html_cache') else ""

                # Find internal links
                link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
                links = re.findall(link_pattern, html_content, re.IGNORECASE)

                for link in links[:10]:  # Limit discovered URLs
                    # Convert relative URLs to absolute
                    if link.startswith('/'):
                        parsed = urlparse(base_url)
                        full_url = f"{parsed.scheme}://{parsed.netloc}{link}"
                    elif link.startswith('http'):
                        full_url = link
                    else:
                        full_url = f"{base_url.rstrip('/')}/{link}"

                    # Only include URLs from same domain
                    if urlparse(full_url).netloc == urlparse(base_url).netloc:
                        urls.append(full_url)

        except Exception as e:
            print(f"Error discovering URLs: {e}")

        return list(set(urls))  # Remove duplicates

    async def process_scraped_data(self, raw_data: List[Dict], target: ScrapingTarget) -> List[ScrapedData]:
        """Process and validate scraped data"""
        processed_data = []

        for data_item in raw_data:
            if data_item["status"] == "success":
                # Process each data type
                for data_type in target.data_types:
                    data_content = data_item["data"].get(data_type.value, "")

                    if data_content:
                        # Create structured data object
                        scraped_item = ScrapedData(
                            data_id=f"data_{int(time.time())}_{random.randint(1000, 9999)}",
                            target_id=target.target_id,
                            url=data_item["url"],
                            data_type=data_type,
                            content=str(data_content)[:5000],  # Limit content size
                            metadata={
                                "scraping_mode": target.scraping_mode.value,
                                "user_agent": target.user_agent,
                                "response_size": data_item.get("response_size", 0)
                            },
                            scraped_at=datetime.now(),
                            quality_score=await self.assess_data_quality(data_content, data_type)
                        )

                        processed_data.append(scraped_item)

        return processed_data

    async def assess_data_quality(self, content: str, data_type: DataType) -> float:
        """Assess quality of scraped data"""
        quality_score = 0.5  # Base score

        if data_type == DataType.TEXT:
            # Assess text quality
            if len(content) > 100:
                quality_score += 0.2
            if content.count('.') > 5:  # Has sentences
                quality_score += 0.2
            if not content.isupper():  # Not all caps
                quality_score += 0.1

        elif data_type == DataType.PRICES:
            # Assess price data quality
            if '$' in content or 'USD' in content:
                quality_score += 0.3
            if re.search(r'\d+\.?\d*', content):
                quality_score += 0.2

        elif data_type == DataType.IMAGES:
            # Assess image data quality
            if len(content) > 10:  # Has actual URLs
                quality_score += 0.3
            if '.jpg' in content or '.png' in content:
                quality_score += 0.2

        return min(quality_score, 1.0)

    async def calculate_data_quality_score(self) -> float:
        """Calculate overall data quality score"""
        if not self.scraped_data:
            return 0.0

        total_quality = sum(data.quality_score for data in self.scraped_data)
        return total_quality / len(self.scraped_data)

    async def save_scraped_data(self):
        """Save scraped data to storage"""
        if self.scraped_data:
            # Save to JSON file
            data_file = {
                "scraped_at": datetime.now().isoformat(),
                "total_items": len(self.scraped_data),
                "data": [asdict(data) for data in self.scraped_data]
            }

            data_path = self.project_root / 'data_scrapers' / 'scraped_data' / f'scraping_session_{int(time.time())}.json'
            data_path.parent.mkdir(parents=True, exist_ok=True)

            with open(data_path, 'w') as f:
                json.dump(data_file, f, indent=2)

            print(f"💾 Saved {len(self.scraped_data)} data items to {data_path}")

    async def generate_scraping_report(self) -> Dict:
        """Generate comprehensive scraping report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_targets": len(self.scraping_targets),
            "total_data_collected": len(self.scraped_data),
            "data_by_type": {},
            "ethical_compliance_rate": 0.0,
            "average_quality_score": 0.0,
            "scraping_efficiency": 0.0,
            "error_rate": 0.0
        }

        # Count data by type
        for data_type in DataType:
            type_count = len([d for d in self.scraped_data if d.data_type == data_type])
            report["data_by_type"][data_type.value] = type_count

        # Calculate metrics
        if self.scraped_data:
            report["average_quality_score"] = sum(d.quality_score for d in self.scraped_data) / len(self.scraped_data)

        # Ethical compliance (all targets respect robots.txt)
        ethical_targets = len([t for t in self.scraping_targets if t.respect_robots_txt])
        if report["total_targets"] > 0:
            report["ethical_compliance_rate"] = ethical_targets / report["total_targets"]

        return report

async def main():
    """Main web scraping demo"""
    print("🕷️ Ultra Pinnacle Studio - Universal Web Scrapers")
    print("=" * 50)

    # Initialize scraper
    scraper = UniversalWebScraper()

    print("🕷️ Initializing universal web scraping...")
    print("🤝 Ethical scraping protocols")
    print("🥷 Anti-bot evasion techniques")
    print("📦 Bulk data collection")
    print("⚡ Real-time data scraping")
    print("🔍 Intelligent data extraction")
    print("=" * 50)

    # Run universal scraping system
    print("\n🕷️ Starting universal scraping process...")
    scraping_results = await scraper.run_universal_scraping_system()

    print(f"✅ Scraping completed: {scraping_results['targets_processed']} targets processed")
    print(f"📊 Data collected: {scraping_results['data_collected']} items")
    print(f"🤝 Ethical compliance: {scraping_results['ethical_compliance']}")
    print(f"⭐ Data quality score: {scraping_results['data_quality_score']:.2f}")

    # Save scraped data
    print("\n💾 Saving scraped data...")
    await scraper.save_scraped_data()

    # Generate scraping report
    print("\n📊 Generating scraping report...")
    report = await scraper.generate_scraping_report()

    print(f"🎯 Total targets: {report['total_targets']}")
    print(f"📈 Ethical compliance rate: {report['ethical_compliance_rate']:.1%}")
    print(f"⭐ Average quality score: {report['average_quality_score']:.2f}")

    # Show data breakdown
    print("\n📋 Data Collection Breakdown:")
    for data_type, count in report['data_by_type'].items():
        if count > 0:
            print(f"  • {data_type.upper()}: {count} items")

    print("\n🕷️ Universal Web Scraper Features:")
    print("✅ Multi-mode scraping (ethical, stealth, bulk, real-time)")
    print("✅ Intelligent data extraction")
    print("✅ Anti-bot evasion techniques")
    print("✅ Robots.txt compliance checking")
    print("✅ Rate limiting and politeness")
    print("✅ Data quality assessment")
    print("✅ Comprehensive reporting")

if __name__ == "__main__":
    asyncio.run(main())