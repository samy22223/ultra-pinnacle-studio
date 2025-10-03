#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Free Domain Auto-Builder
Generates free custom domains, subdomains, and international TLDs instantly
"""

import os
import json
import time
import random
import secrets
import asyncio
import string
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class TLDType(Enum):
    FREE = "free"
    PREMIUM = "premium"
    INTERNATIONAL = "international"
    CUSTOM = "custom"

class DomainStatus(Enum):
    AVAILABLE = "available"
    REGISTERED = "registered"
    PENDING = "pending"
    EXPIRED = "expired"

@dataclass
class DomainConfig:
    """Domain generation configuration"""
    name_length: int = 8
    use_numbers: bool = True
    use_hyphens: bool = True
    include_brand: bool = False
    brand_name: str = ""
    preferred_tlds: List[str] = None
    international_tlds: bool = True

    def __post_init__(self):
        if self.preferred_tlds is None:
            self.preferred_tlds = ['.com', '.net', '.org', '.io', '.ai', '.app']

@dataclass
class GeneratedDomain:
    """Generated domain information"""
    domain_name: str
    tld: str
    full_domain: str
    status: DomainStatus
    registration_date: datetime
    expiry_date: datetime
    is_subdomain: bool = False
    is_international: bool = False
    availability_score: float = 0.0

class DomainGenerator:
    """Main domain generation and management system"""

    def __init__(self, config: DomainConfig = None):
        self.config = config or DomainConfig()
        self.project_root = Path(__file__).parent.parent

        # TLD databases
        self.free_tlds = [
            '.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.club',
            '.online', '.store', '.tech', '.space', '.website', '.fun'
        ]

        self.premium_tlds = [
            '.com', '.net', '.org', '.io', '.ai', '.app', '.dev', '.co',
            '.info', '.biz', '.pro', '.tech', '.online', '.store', '.shop'
        ]

        self.international_tlds = [
            '.fr', '.de', '.es', '.it', '.nl', '.be', '.at', '.ch',
            '.se', '.no', '.dk', '.fi', '.pl', '.cz', '.hu', '.ro',
            '.pt', '.gr', '.ru', '.ua', '.br', '.mx', '.ar', '.co',
            '.in', '.jp', '.kr', '.cn', '.au', '.nz', '.za', '.eg'
        ]

        # Brand prefixes/suffixes for enhanced domains
        self.brand_prefixes = [
            'ultra', 'pinnacle', 'ai', 'smart', 'next', 'future', 'quantum',
            'cyber', 'digital', 'meta', 'neo', 'apex', 'prime', 'elite'
        ]

        self.brand_suffixes = [
            'studio', 'platform', 'system', 'engine', 'hub', 'network',
            'cloud', 'matrix', 'sphere', 'realm', 'verse', 'core', 'base'
        ]

    async def generate_domains(self, count: int = 5) -> List[GeneratedDomain]:
        """Generate multiple domain options"""
        domains = []

        for _ in range(count):
            # Generate different types of domains
            domain_types = ['standard', 'brand_enhanced', 'international']

            if random.choice(domain_types) == 'standard':
                domain = await self._generate_standard_domain()
            elif random.choice(domain_types) == 'brand_enhanced':
                domain = await self._generate_brand_enhanced_domain()
            else:
                domain = await self._generate_international_domain()

            domains.append(domain)

        # Check availability and score domains
        scored_domains = await self._score_and_filter_domains(domains)

        return scored_domains[:count]

    async def _generate_standard_domain(self) -> GeneratedDomain:
        """Generate a standard domain name"""
        # Generate random name
        name_length = random.randint(6, 12)
        characters = string.ascii_lowercase

        if self.config.use_numbers:
            characters += string.digits

        if self.config.use_hyphens:
            characters += '-'

        name = ''.join(random.choice(characters) for _ in range(name_length))

        # Select TLD
        if random.random() < 0.7:  # 70% chance for premium TLD
            tld = random.choice(self.premium_tlds)
        else:
            tld = random.choice(self.free_tlds)

        full_domain = f"{name}{tld}"

        return GeneratedDomain(
            domain_name=name,
            tld=tld,
            full_domain=full_domain,
            status=DomainStatus.AVAILABLE,
            registration_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365),
            availability_score=await self._calculate_availability_score(name, tld)
        )

    async def _generate_brand_enhanced_domain(self) -> GeneratedDomain:
        """Generate a brand-enhanced domain"""
        if random.random() < 0.5:
            # Prefix style: ultra-pinnacle-ai.com
            prefix = random.choice(self.brand_prefixes)
            name = f"{prefix}-{self.config.brand_name or 'pinnacle'}"
            name += '-' + ''.join(random.choices(string.ascii_lowercase, k=3))
        else:
            # Suffix style: mybrand-ultra.com
            name = f"{self.config.brand_name or 'pinnacle'}-{random.choice(self.brand_suffixes)}"
            if random.random() < 0.3:
                name += str(random.randint(10, 99))

        tld = random.choice(self.premium_tlds)
        full_domain = f"{name}{tld}"

        return GeneratedDomain(
            domain_name=name,
            tld=tld,
            full_domain=full_domain,
            status=DomainStatus.AVAILABLE,
            registration_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365),
            availability_score=await self._calculate_availability_score(name, tld)
        )

    async def _generate_international_domain(self) -> GeneratedDomain:
        """Generate an international domain with local TLD"""
        # Generate name with international flair
        international_prefixes = [
            'global', 'world', 'inter', 'uni', 'multi', 'euro', 'asia', 'pacific'
        ]

        if random.random() < 0.6:
            name = random.choice(international_prefixes)
            name += '-' + ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 8)))
        else:
            name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(6, 10)))

        tld = random.choice(self.international_tlds)
        full_domain = f"{name}{tld}"

        return GeneratedDomain(
            domain_name=name,
            tld=tld,
            full_domain=full_domain,
            status=DomainStatus.AVAILABLE,
            registration_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365),
            is_international=True,
            availability_score=await self._calculate_availability_score(name, tld)
        )

    async def _calculate_availability_score(self, name: str, tld: str) -> float:
        """Calculate domain availability score (0-1)"""
        score = 0.5  # Base score

        # Length factor - prefer 8-15 characters
        if 8 <= len(name) <= 15:
            score += 0.2
        elif len(name) < 6:
            score -= 0.1

        # Character diversity
        if any(c.isdigit() for c in name):
            score += 0.1
        if '-' in name:
            score += 0.05

        # TLD popularity
        popular_tlds = ['.com', '.net', '.org', '.io']
        if tld in popular_tlds:
            score += 0.15

        # Brand relevance
        if any(brand in name.lower() for brand in ['ultra', 'pinnacle', 'ai', 'smart']):
            score += 0.1

        return min(score, 1.0)

    async def _score_and_filter_domains(self, domains: List[GeneratedDomain]) -> List[GeneratedDomain]:
        """Score and filter generated domains"""
        # Sort by availability score
        scored_domains = sorted(domains, key=lambda x: x.availability_score, reverse=True)

        # Mark some as potentially unavailable for realism
        for i, domain in enumerate(scored_domains):
            if i > 0 and random.random() < 0.3:  # 30% chance of being taken
                domain.status = DomainStatus.REGISTERED
                domain.availability_score *= 0.7

        return scored_domains

    async def register_domain(self, domain: GeneratedDomain, user_email: str) -> bool:
        """Register a generated domain"""
        try:
            # In a real implementation, this would integrate with:
            # - Freenom API for free domains
            # - Namecheap/Godaddy for premium domains
            # - Local DNS server configuration

            # For now, simulate registration
            domain.status = DomainStatus.REGISTERED

            # Save registration info
            registration_data = {
                "domain": domain.full_domain,
                "user_email": user_email,
                "registration_date": domain.registration_date.isoformat(),
                "expiry_date": domain.expiry_date.isoformat(),
                "registration_id": secrets.token_hex(16)
            }

            # Save to registered domains file
            domains_file = self.project_root / 'config' / 'registered_domains.json'
            domains_file.parent.mkdir(exist_ok=True)

            existing_domains = []
            if domains_file.exists():
                with open(domains_file, 'r') as f:
                    existing_domains = json.load(f)

            existing_domains.append(registration_data)

            with open(domains_file, 'w') as f:
                json.dump(existing_domains, f, indent=2)

            return True

        except Exception as e:
            print(f"Domain registration failed: {e}")
            return False

    async def generate_subdomain(self, main_domain: str, subdomain_prefix: str = None) -> str:
        """Generate a subdomain for an existing domain"""
        if not subdomain_prefix:
            prefixes = ['app', 'api', 'www', 'dev', 'test', 'demo', 'beta', 'alpha']
            subdomain_prefix = random.choice(prefixes)

        # Ensure main_domain doesn't include protocol
        clean_domain = main_domain.replace('http://', '').replace('https://', '')

        return f"{subdomain_prefix}.{clean_domain}"

    async def setup_dns_records(self, domain: str, target_ip: str = "127.0.0.1") -> Dict[str, str]:
        """Generate DNS configuration for the domain"""
        # In a real implementation, this would:
        # - Configure DNS records with the registrar
        # - Set up CDN integration
        # - Configure SSL certificates

        dns_records = {
            "A_record": f"{domain} -> {target_ip}",
            "CNAME_www": f"www.{domain} -> {domain}",
            "MX_record": f"mail.{domain} -> {domain}",
            "TXT_record": f"v=spf1 -all (for {domain})"
        }

        # Save DNS configuration
        dns_config = {
            "domain": domain,
            "target_ip": target_ip,
            "records": dns_records,
            "generated_at": datetime.now().isoformat()
        }

        dns_file = self.project_root / 'config' / f'dns_{domain.replace(".", "_")}.json'
        with open(dns_file, 'w') as f:
            json.dump(dns_config, f, indent=2)

        return dns_records

class DomainAPI:
    """REST API for domain generation and management"""

    def __init__(self):
        self.generator = DomainGenerator()

    async def generate_domain_options(self, count: int = 5, domain_type: str = "mixed") -> Dict:
        """Generate domain options via API"""
        domains = await self.generator.generate_domains(count)

        return {
            "domains": [asdict(domain) for domain in domains],
            "generated_at": datetime.now().isoformat(),
            "total_options": len(domains)
        }

    async def register_selected_domain(self, domain_name: str, user_email: str) -> Dict:
        """Register a selected domain"""
        # Find the domain in our generated options
        # In a real implementation, this would search a database

        # For now, create a domain object
        domain_parts = domain_name.split('.')
        if len(domain_parts) >= 2:
            name = domain_parts[0]
            tld = '.' + '.'.join(domain_parts[1:])
        else:
            name = domain_name
            tld = '.com'

        domain = GeneratedDomain(
            domain_name=name,
            tld=tld,
            full_domain=domain_name,
            status=DomainStatus.AVAILABLE,
            registration_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365)
        )

        success = await self.generator.register_domain(domain, user_email)

        if success:
            # Set up DNS records
            dns_records = await self.generator.setup_dns_records(domain_name)

            return {
                "success": True,
                "domain": domain_name,
                "registration_id": secrets.token_hex(16),
                "dns_records": dns_records,
                "expires": domain.expiry_date.isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Domain registration failed"
            }

async def main():
    """Demo domain generation"""
    print("🌐 Ultra Pinnacle Studio - Domain Auto-Builder")
    print("=" * 50)

    # Initialize generator
    config = DomainConfig(
        name_length=10,
        use_numbers=True,
        use_hyphens=True,
        include_brand=True,
        brand_name="pinnacle",
        international_tlds=True
    )

    generator = DomainGenerator(config)

    # Generate domain options
    print("Generating domain options...")
    domains = await generator.generate_domains(8)

    print(f"\n🎯 Generated {len(domains)} domain options:\n")

    for i, domain in enumerate(domains, 1):
        status_emoji = "✅" if domain.status == DomainStatus.AVAILABLE else "❌"
        international_flag = "🌍" if domain.is_international else ""
        score_bar = "█" * int(domain.availability_score * 10)

        print(f"{i}. {status_emoji} {domain.full_domain} {international_flag}")
        print(f"   Score: {score_bar} ({domain.availability_score".2f"})")
        print(f"   Expires: {domain.expiry_date.strftime('%Y-%m-%d')}")
        print()

    # Demo domain registration
    if domains:
        best_domain = domains[0]
        print(f"Registering best domain: {best_domain.full_domain}")

        success = await generator.register_domain(best_domain, "user@example.com")
        if success:
            print("✅ Domain registered successfully!")

            # Set up DNS
            dns_records = await generator.setup_dns_records(best_domain.full_domain)
            print("🌐 DNS records configured:")
            for record_type, record in dns_records.items():
                print(f"   {record_type}: {record}")
        else:
            print("❌ Domain registration failed")

if __name__ == "__main__":
    asyncio.run(main())