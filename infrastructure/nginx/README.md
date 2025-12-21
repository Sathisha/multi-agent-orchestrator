# Nginx Security Layer

This directory contains Nginx configuration for the AI Agent Framework security layer.

## Features

- **SSL/TLS Termination**: HTTPS with TLS 1.2/1.3
- **Security Headers**: Comprehensive security headers (HSTS, CSP, X-Frame-Options, etc.)
- **Rate Limiting**: API rate limiting and DDoS protection
- **Reverse Proxy**: Proxying requests to backend services
- **Access Control**: IP-based access restrictions for sensitive endpoints

## SSL Certificates

For development, generate self-signed certificates:

```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/server.key \
  -out ssl/server.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

For production, use Let's Encrypt or your organization's certificates.

## Configuration

The main configuration file is `nginx.conf`. Key settings:

- **Rate Limiting**: 10 requests/second for API, 1 request/second for login
- **Connection Limits**: 20 concurrent connections per IP
- **SSL Protocols**: TLS 1.2 and 1.3 only
- **Security Headers**: All modern security headers enabled

## Testing

Test the configuration:

```bash
docker-compose -f docker-compose.security.yml exec nginx nginx -t
```

Reload configuration:

```bash
docker-compose -f docker-compose.security.yml exec nginx nginx -s reload
```

## Monitoring

Access logs: `/var/log/nginx/access.log`
Error logs: `/var/log/nginx/error.log`

## Security Best Practices

1. **Always use HTTPS in production**
2. **Keep SSL certificates up to date**
3. **Monitor rate limiting logs for attacks**
4. **Regularly update Nginx to latest version**
5. **Restrict metrics endpoint to internal networks only**
6. **Use strong SSL ciphers and protocols**

## Customization

To customize rate limits, edit the `limit_req_zone` directives in `nginx.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

To add IP whitelist/blacklist, use `allow` and `deny` directives:

```nginx
location /admin/ {
    allow 192.168.1.0/24;
    deny all;
    # ...
}
```