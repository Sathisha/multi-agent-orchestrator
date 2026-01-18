-- RBAC Role Seeding Script
-- Seeds the 4 system roles: view_user, standard_user, service_user, super_admin

DO $$
BEGIN
    -- Insert view_user role
    IF NOT EXISTS (SELECT 1 FROM roles WHERE name = 'view_user') THEN
        INSERT INTO roles (name, display_name, description, permission_level, is_system_role, is_default, id, created_at, updated_at)
        VALUES ('view_user', 'View User', 'Read-only access to view agents and workflows', 1, true, false, gen_random_uuid(), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        RAISE NOTICE 'Created role: view_user';
    ELSE
        RAISE NOTICE 'Role view_user already exists';
    END IF;

    -- Insert standard_user role
    IF NOT EXISTS (SELECT 1 FROM roles WHERE name = 'standard_user') THEN
        INSERT INTO roles (name, display_name, description, permission_level, is_system_role, is_default, id, created_at, updated_at)
        VALUES ('standard_user', 'Standard User', 'Can execute agents and workflows', 2, true, true, gen_random_uuid(), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        RAISE NOTICE 'Created role: standard_user';
    ELSE
        RAISE NOTICE 'Role standard_user already exists';
    END IF;

    -- Insert service_user role
    IF NOT EXISTS (SELECT 1 FROM roles WHERE name = 'service_user') THEN
        INSERT INTO roles (name, display_name, description, permission_level, is_system_role, is_default, id, created_at, updated_at)
        VALUES ('service_user', 'Service User', 'Full CRUD access to agents and workflows', 3, true, false, gen_random_uuid(), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        RAISE NOTICE 'Created role: service_user';
    ELSE
        RAISE NOTICE 'Role service_user already exists';
    END IF;

    -- Insert super_admin role
    IF NOT EXISTS (SELECT 1 FROM roles WHERE name = 'super_admin') THEN
        INSERT INTO roles (name, display_name, description, permission_level, is_system_role, is_default, id, created_at, updated_at)
        VALUES ('super_admin', 'Super Administrator', 'Full system administration access', 4, true, false, gen_random_uuid(), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        RAISE NOTICE 'Created role: super_admin';
    ELSE
        RAISE NOTICE 'Role super_admin already exists';
    END IF;

    -- Assign super_admin role to admin@example.com if exists
    IF EXISTS (SELECT 1 FROM users WHERE email = 'admin@example.com') THEN
        UPDATE users SET is_superuser = true WHERE email = 'admin@example.com';
        
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id 
        FROM users u 
        CROSS JOIN roles r 
        WHERE u.email = 'admin@example.com' 
        AND r.name = 'super_admin'
        AND NOT EXISTS (
            SELECT 1 FROM user_roles ur 
            WHERE ur.user_id = u.id AND ur.role_id = r.id
        );
        
        RAISE NOTICE 'Assigned super_admin role to admin@example.com';
    ELSE
        RAISE NOTICE 'User admin@example.com not found';
    END IF;

END $$;

-- Verify seeding
SELECT 
    'ROLES SEEDED:' as status,
    COUNT(*) as total_roles
FROM roles;

SELECT 
    name,
    display_name,
    permission_level,
    is_system_role,
    is_default
FROM roles 
ORDER BY permission_level;

-- Verify admin user
SELECT 
    'ADMIN USER:' as status,
    u.email,
    u.is_superuser,
    r.name as role_name,
    r.permission_level
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
WHERE u.email = 'admin@example.com';
