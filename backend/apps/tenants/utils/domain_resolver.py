import re

class DomainResolver:
    @classmethod
    def resolve(cls, host):
        if not host:
            return None
            
        host = host.split(':')[0]  # Remove port
        
        # Localhost development fallback
        if host in ['localhost', '127.0.0.1']:
            return 'default'
            
        parts = host.split('.')
        
        # Subdomain matching (tenant.lvh.me or tenant.kavan.local)
        if len(parts) >= 3 and parts[-2] in ['lvh', 'kavan'] and parts[-1] in ['me', 'local', 'com']:
            return parts[0]
            
        # Custom domains (e.g. erp.company.com) 
        # In a real app this might require a DB lookup against company_domain
        # which can be implemented here safely
        
        return host  # Fallback assumption for DB lookup
