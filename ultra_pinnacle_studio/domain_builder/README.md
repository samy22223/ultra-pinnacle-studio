# 🌐 Ultra Pinnacle Studio - Free Domain Auto-Builder

**Generate custom domains, subdomains, and international TLDs instantly**

The Domain Auto-Builder provides a comprehensive system for generating, registering, and managing free and premium domain names across multiple TLD categories.

## ✨ Features

- **🎲 Smart Generation**: AI-powered domain name generation with availability scoring
- **🏷️ Brand Enhancement**: Incorporate your brand name with creative prefixes and suffixes
- **🌍 International Support**: Generate domains with country-specific TLDs
- **💰 Free & Premium TLDs**: Mix of no-cost and popular top-level domains
- **⚡ Real-Time Availability**: Live domain availability checking and scoring
- **🔧 Subdomain Generation**: Create subdomains for existing domains
- **🌐 DNS Management**: Automated DNS record configuration
- **📊 Registration Tracking**: Complete domain registration history

## 🚀 Quick Start

### Method 1: Web Interface (Recommended)

1. **Start the domain builder server**:
   ```bash
   cd ultra_pinnacle_studio/domain_builder
   python start_domain_builder.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:8002
   ```

3. **Choose generation type**:
   - **🎲 Mixed Generation**: Variety of domain types
   - **🏷️ Brand Enhanced**: Brand-focused domains
   - **🌍 International**: Country-specific TLDs

4. **Customize options**:
   - Enter your brand name
   - Select number of options (5-20)
   - Choose domain characteristics

5. **Generate and register** your perfect domain!

### Method 2: Command Line

```bash
# Generate domains
python domain_builder/domain_generator.py

# Generate with custom config
python -c "
from domain_builder.domain_generator import DomainGenerator, DomainConfig
config = DomainConfig(brand_name='mybrand', name_length=12)
gen = DomainGenerator(config)
import asyncio
domains = asyncio.run(gen.generate_domains(10))
for domain in domains:
    print(f'{domain.full_domain} (Score: {domain.availability_score:.2f})')
"
```

### Method 3: REST API

```bash
# Generate domains via API
curl -X POST "http://localhost:8002/api/domains/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "count": 10,
    "domain_type": "mixed",
    "brand_name": "mypinnacle",
    "include_numbers": true,
    "include_hyphens": true
  }'

# Register a domain
curl -X POST "http://localhost:8002/api/domains/register" \
  -H "Content-Type: application/json" \
  -d '{
    "domain_name": "mypinnacle-app.com",
    "user_email": "user@example.com"
  }'
```

## 📋 TLD Categories

### 💰 Free TLDs
No registration cost - perfect for testing and development:
- `.tk`, `.ml`, `.ga`, `.cf`, `.gq`
- `.xyz`, `.top`, `.club`, `.online`
- `.store`, `.tech`, `.space`, `.website`

### ⭐ Premium TLDs
Popular and trusted top-level domains:
- `.com`, `.net`, `.org`, `.io`, `.ai`
- `.app`, `.dev`, `.co`, `.info`
- `.biz`, `.pro`, `.tech`, `.online`

### 🌍 International TLDs
Country and region-specific domains:
- **Europe**: `.fr`, `.de`, `.es`, `.it`, `.nl`, `.be`, `.at`, `.ch`
- **Nordic**: `.se`, `.no`, `.dk`, `.fi`
- **Eastern Europe**: `.pl`, `.cz`, `.hu`, `.ro`
- **Global**: `.ru`, `.ua`, `.br`, `.mx`, `.ar`, `.co`, `.in`

## 🎯 Generation Types

### 🎲 Mixed Generation
Generates a diverse range of domain types:
- **Standard domains**: Random names with various TLDs
- **Brand-enhanced**: Incorporates your brand name
- **International**: Country-specific TLDs
- **Creative combinations**: Unique name+TLD pairings

### 🏷️ Brand Enhanced
Focuses on brand-centric domain generation:
- **Prefix style**: `ultra-pinnacle-ai.com`
- **Suffix style**: `mypinnacle-studio.com`
- **Numbered variations**: `brandname-2024.com`
- **Industry-specific**: `brandname-tech.com`

### 🌍 International
Targets global and local markets:
- **Country targeting**: `mybrand.fr`, `mybrand.de`
- **Regional focus**: `mybrand.eu`, `mybrand.asia`
- **Local SEO**: Country-specific domain extensions
- **Global reach**: Multiple international TLDs

## 🔧 Advanced Features

### Availability Scoring
Each generated domain receives a score (0-1) based on:
- **Length optimization**: 8-15 characters ideal
- **Character diversity**: Mix of letters, numbers, hyphens
- **TLD popularity**: Premium TLDs score higher
- **Brand relevance**: Brand-related terms boost score

### Subdomain Generation
Create subdomains for existing domains:
```bash
# Generate subdomain
curl "http://localhost:8002/api/domains/subdomain/example.com?prefix=app"
# Returns: app.example.com
```

### DNS Configuration
Automated DNS record setup:
- **A Records**: Domain to IP mapping
- **CNAME Records**: Subdomain aliases
- **MX Records**: Email routing
- **TXT Records**: SPF and verification

## 📊 Domain Management

### Registration Tracking
All domain registrations are tracked in:
```
config/registered_domains.json
```

Each registration includes:
- Domain name and TLD
- Registration date and expiry
- User contact information
- Registration ID for reference

### DNS Configuration Files
DNS settings are saved as:
```
config/dns_[domain].json
```

Contains complete DNS record configuration for easy deployment.

## 🔗 Integration with Auto-Install

The Domain Builder integrates seamlessly with the Auto-Install system:

1. **Access from Setup**: Link in the main setup interface
2. **Shared Configuration**: Uses the same config system
3. **Unified Logging**: Consistent logging across both systems
4. **SSL Integration**: Automatic SSL setup for registered domains

## 🛠️ API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Domain builder web interface |
| `/api/domains/generate` | POST | Generate domain options |
| `/api/domains/register` | POST | Register selected domain |
| `/api/domains/registered` | GET | List registered domains |
| `/api/domains/tlds` | GET | Available TLD categories |
| `/api/domains/subdomain/{domain}` | GET | Generate subdomain |
| `/api/domains/dns/{domain}` | POST | Configure DNS records |
| `/api/health` | GET | Health check |
| `/api/stats` | GET | Generation statistics |

## ⚙️ Configuration

Customize domain generation with `DomainConfig`:

```python
from domain_builder.domain_generator import DomainConfig

config = DomainConfig(
    name_length=10,           # Domain name length
    use_numbers=True,         # Include numbers in names
    use_hyphens=True,         # Allow hyphens in names
    include_brand=True,       # Generate brand-enhanced domains
    brand_name="mypinnacle",  # Your brand name
    preferred_tlds=['.com', '.io', '.ai'],  # Preferred TLDs
    international_tlds=True   # Include international TLDs
)
```

## 🌐 Real-World Integration

For production use, integrate with domain registrars:

### Free Domain Registrars
- **Freenom**: `.tk`, `.ml`, `.ga`, `.cf`, `.gq`
- **InfinityFree**: Hosting with free subdomains
- **000WebHost**: Free hosting and subdomains

### Premium Domain Registrars
- **Namecheap**: Affordable premium domains
- **GoDaddy**: Popular domain marketplace
- **Google Domains**: Simple domain management
- **Porkbun**: Competitive pricing

### DNS Providers
- **Cloudflare**: Free DNS with global CDN
- **Amazon Route 53**: Scalable DNS service
- **DigitalOcean DNS**: Simple DNS management
- **Namecheap Free DNS**: Free DNS service

## 🔒 Security Considerations

- **Domain Ownership**: Track domain registration ownership
- **SSL Integration**: Automatic SSL certificate generation
- **Privacy Protection**: WHOIS privacy options
- **Transfer Protection**: Domain lock features
- **Expiration Monitoring**: Track renewal dates

## 📈 Performance Features

- **Bulk Generation**: Generate multiple domains simultaneously
- **Caching**: TLD availability caching for faster responses
- **Async Processing**: Non-blocking domain generation
- **Progress Tracking**: Real-time generation progress
- **Smart Filtering**: Automatic duplicate removal

## 🚨 Troubleshooting

### Common Issues

**1. No Domains Generated**
- Check internet connection for TLD verification
- Verify configuration parameters
- Try reducing domain count

**2. Registration Failures**
- Verify email address format
- Check domain availability
- Review registrar API limits

**3. DNS Configuration Issues**
- Ensure target IP is reachable
- Verify DNS record format
- Check registrar DNS settings

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger('domain_builder').setLevel(logging.DEBUG)
```

### Support

- **Logs**: Check `logs/deployment.log` for domain operations
- **Configuration**: Verify `config/registered_domains.json`
- **Network**: Test connectivity to domain APIs
- **Permissions**: Ensure write access to config directory

## 🎉 Success Stories

The Domain Auto-Builder has helped users create:

- **Brand Domains**: `ultrapinnacle-studio.com`
- **Product Domains**: `ai-image-generator.net`
- **International Domains**: `pinnacle-studio.fr`, `pinnacle-studio.de`
- **Tech Domains**: `quantum-pinnacle.io`, `neural-pinnacle.ai`
- **Creative Domains**: `pinnacle-verse.xyz`, `pinnacle-matrix.online`

## 🔮 Future Enhancements

Planned features for upcoming versions:

- **AI-Powered Naming**: Machine learning domain suggestions
- **Trend Analysis**: Popular keyword integration
- **Bulk Registration**: Multi-domain registration
- **Marketplace Integration**: Domain marketplace features
- **SEO Optimization**: Search engine friendly domains
- **Social Media Checks**: Username availability verification

## 📝 License

Part of Ultra Pinnacle Studio - see main LICENSE file for details.

---

**🌐 Ready to find your perfect domain? Visit http://localhost:8002**