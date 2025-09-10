import xmlrpc.client
import ssl

# Disable SSL verification (useful for development with self-signed certificates)
ssl._create_default_https_context = ssl._create_unverified_context

# Odoo connection information
url = 'http://localhost:8018'  # Base Odoo URL (no /odoo/ at the end)
db = 'admin18'  # Your database name
username = 'admin'  # Your Odoo username
password = 'admin123'  # Your Odoo password

# Connect to the common service
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')

# Authenticate and get user ID
uid = common.authenticate(db, username, password, {})
print("Authenticated UID:", uid)

if not uid:
    raise Exception("Authentication failed. Check DB, username, or password.")

# Connect to the object service
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Search for all properties
property_ids = models.execute_kw(db, uid, password,
                                 'property.property', 'search', [[]])  # Empty domain = all records

# Read the properties
properties = models.execute_kw(db, uid, password,
                               'property.property', 'read', [property_ids],
                               {'fields': ['name', 'property_kind', 'monthly_rate', 'is_available']})

# Print the results
print("Found {} properties:".format(len(properties)))
for prop in properties:
    print("- {} ({}) - ${}/month - Available: {}".format(
        prop['name'],
        prop['property_kind'],
        prop['monthly_rate'],
        prop['is_available']
    ))


def create_property():
    """Create a new property through the API - handles all constraints"""
    property_data = {
        'name': 'API Created Property',
        'property_kind': 'apartment',
        'monthly_rate': 1200.0,
        'is_available': True,
        'address': '123 API Street, Code City',
        'expected_price': 250000.0,
        'selling_price': 0.0,
        'description': 'Property created via API integration',
        'state': 'draft',
    }

    try:
        new_property_id = models.execute_kw(db, uid, password, 'property.property', 'create', [property_data])
        print(f"Created new property with ID: {new_property_id}")
        return new_property_id
    except Exception as e:
        print(f"Create failed: {e}")
        return None


def create_property_with_tenant():
    """Create a property that's already rented (with tenant)"""
    try:
        # FIRST create the tenant (without property assignment)
        tenant_data = {
            'name': 'API Test Tenant',
            'email': 'tenant@example.com',
            'phone': '+1234567890'
        }

        tenant_id = models.execute_kw(db, uid, password, 'property.tenant', 'create', [tenant_data])
        print(f"Created tenant with ID: {tenant_id}")

        # NOW create the property with the tenant assigned
        property_data = {
            'name': 'API Rented Property',
            'property_kind': 'apartment',
            'monthly_rate': 1500.0,
            'is_available': False,  # Mark as rented
            'address': '456 Rental Ave, Tenant City',
            'expected_price': 300000.0,
            'selling_price': 0.0,
            'description': 'Property with tenant created via API',
            'state': 'draft',
            'tenant_ids': [(6, 0, [tenant_id])]  # ASSIGN THE EXISTING TENANT
        }

        property_id = models.execute_kw(db, uid, password, 'property.property', 'create', [property_data])
        print(f"Created rented property with ID: {property_id}")

        return property_id

    except Exception as e:
        print(f"Create with tenant failed: {e}")
        # Clean up: delete tenant if property creation failed
        if 'tenant_id' in locals():
            models.execute_kw(db, uid, password, 'property.tenant', 'unlink', [[tenant_id]])
        return None


def create_tenant(property_id):
    """Create a tenant and assign to property"""
    tenant_data = {
        'name': 'API Test Tenant',
        'property_id': property_id,
        'email': 'tenant@example.com',
        'phone': '+1234567890'
    }

    try:
        tenant_id = models.execute_kw(db, uid, password, 'property.tenant', 'create', [tenant_data])
        print(f"Created tenant with ID: {tenant_id} for property {property_id}")
        return tenant_id
    except Exception as e:
        print(f"Tenant creation failed: {e}")
        return None


def update_property(property_id):
    """Update a property through the API"""
    update_data = {
        'monthly_rate': 1500.0,
        'description': 'This property was updated via API!',
        'expected_price': 275000.0,
    }

    try:
        result = models.execute_kw(db, uid, password, 'property.property', 'write', [[property_id], update_data])
        print(f"Update successful: {result}")
        return result
    except Exception as e:
        print(f"Update failed: {e}")
        return False


def delete_property(property_id):
    """Delete a property through the API"""
    try:
        # First, delete any tenants to avoid constraint errors
        tenant_ids = models.execute_kw(db, uid, password, 'property.tenant', 'search',
                                       [[('property_id', '=', property_id)]])
        if tenant_ids:
            models.execute_kw(db, uid, password, 'property.tenant', 'unlink', [tenant_ids])
            print(f"Deleted {len(tenant_ids)} tenants")

        # Then delete the property
        result = models.execute_kw(db, uid, password, 'property.property', 'unlink', [[property_id]])
        print(f"Deleted property: {result}")
        return result
    except Exception as e:
        print(f"Delete failed: {e}")
        return False


# Test the CRUD operations with error handling
print("\n" + "=" * 50)
print("TESTING FULL CRUD OPERATIONS WITH ERROR HANDLING")
print("=" * 50)

print("\n=== Testing CREATE Operation (Available Property) ===")
new_id = create_property()

if new_id:
    print("\n=== Testing READ Operation (verifying creation) ===")
    new_property = models.execute_kw(db, uid, password, 'property.property', 'read', [new_id])
    print(f"New property details: {new_property[0]}")

    print("\n=== Testing UPDATE Operation ===")
    update_property(new_id)

    # Read again to verify update
    updated_property = models.execute_kw(db, uid, password, 'property.property', 'read', [new_id])
    print(f"Updated monthly rate: ${updated_property[0]['monthly_rate']}")

    print("\n=== Testing DELETE Operation ===")
    delete_property(new_id)
else:
    print("Available property creation failed")

print("\n=== Testing CREATE Operation (Property with Tenant) ===")
rented_id = create_property_with_tenant()

if rented_id:
    print(f"Successfully created rented property with ID: {rented_id}")

    print("\n=== Testing DELETE of Rented Property ===")
    delete_property(rented_id)

print("\n=== Final Verification ===")
remaining_properties = models.execute_kw(db, uid, password, 'property.property', 'search', [[]])
print(f"Remaining properties after operations: {len(remaining_properties)}")