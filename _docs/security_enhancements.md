# Security Enhancements

This document outlines the security enhancements implemented in the Django-Supabase template to protect against common vulnerabilities and threats.

## Table of Contents

1. [OWASP Dependency Scanning](#owasp-dependency-scanning)
2. [API Rate Limiting by IP Address](#api-rate-limiting-by-ip-address)
3. [Additional Security Recommendations](#additional-security-recommendations)

## OWASP Dependency Scanning

We've implemented automated dependency scanning in our CI/CD pipeline using OWASP tools to identify and mitigate vulnerabilities in project dependencies.

### Implementation Details

- **GitHub Actions Workflow**: A dedicated workflow (`security-scan.yml`) runs on push, pull requests, and weekly schedules.
- **Tools Used**:
  - **Safety**: Python package vulnerability scanner
  - **OWASP Dependency-Check**: Comprehensive dependency vulnerability scanner
  - **Bandit**: Python code security scanner

### Benefits

- Early detection of security vulnerabilities in dependencies
- Automated scanning on every code change
- Regular weekly scans to catch newly discovered vulnerabilities
- Comprehensive reports for security auditing

### Usage

The security scan runs automatically, but you can also run it manually:

```bash
# Install safety and bandit locally
pip install safety bandit

# Run safety check
safety check -r requirements.txt

# Run bandit scan
bandit -r backend/
```

## API Rate Limiting by IP Address

We've implemented IP-based rate limiting to protect against brute force attacks, DDoS attempts, and API abuse.

### Implementation Details

- **IP Rate Throttle**: Limits requests from a single IP address regardless of authentication status
- **IP-Based User Rate Throttle**: Combines user ID and IP address for more granular control
- **Default Rate Limits**:
  - IP-based: 1000 requests per hour
  - User+IP-based: 500 requests per hour

### Benefits

- Protection against brute force attacks
- Mitigation of DDoS attempts
- Prevention of API abuse from distributed sources
- Identification of credential sharing (same user from multiple IPs)

### Configuration

Rate limits can be configured through environment variables:

```python
# In settings.py
"DEFAULT_THROTTLE_RATES": {
    "anon": os.getenv("DEFAULT_THROTTLE_RATES_ANON", "100/day"),
    "user": os.getenv("DEFAULT_THROTTLE_RATES_USER", "1000/day"),
    "premium": os.getenv("DEFAULT_THROTTLE_RATES_PREMIUM", "5000/day"),
    "ip": os.getenv("DEFAULT_THROTTLE_RATES_IP", "1000/hour"),
    "user_ip": os.getenv("DEFAULT_THROTTLE_RATES_USER_IP", "500/hour"),
}
```

You can adjust these limits in your `.env` file:

```
DEFAULT_THROTTLE_RATES_IP=1000/hour
DEFAULT_THROTTLE_RATES_USER_IP=500/hour
```

## Additional Security Recommendations

1. **Web Application Firewall (WAF)**: Consider implementing a WAF like Cloudflare or AWS WAF for additional protection against common web vulnerabilities.

2. **Security Headers**: Ensure all recommended security headers are properly configured:
   - Content-Security-Policy
   - X-Content-Type-Options
   - X-Frame-Options
   - X-XSS-Protection

3. **Regular Security Audits**: Schedule regular security audits and penetration testing to identify potential vulnerabilities.

4. **Input Validation**: Implement thorough input validation on all API endpoints to prevent injection attacks.

5. **HTTPS Enforcement**: Ensure HTTPS is enforced for all communications.

6. **Logging and Monitoring**: Implement comprehensive logging and monitoring to detect suspicious activities.

7. **Authentication Hardening**: Consider implementing additional authentication security measures like:
   - Multi-factor authentication
   - Account lockout policies
   - Password strength requirements
