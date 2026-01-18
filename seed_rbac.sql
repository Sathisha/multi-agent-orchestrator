-- Seed RBAC Roles and Permissions
-- This script manually seeds the default roles and permissions

-- Insert roles
INSERT INTO roles (id, name, display_name, description, permission_level, is_system_role, is_default, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'view_user', 'View User', 'Read-only access to view agents and workflows', 1, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (gen_random_uuid(), 'standard_user', 'Standard User', 'Can execute agents and workflows', 2, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (gen_random_uuid(), 'service_user', 'Service User', 'Full CRUD access to agents and workflows', 3, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (gen_random_uuid(), 'super_admin', 'Super Administrator', 'Full system administration access', 4, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    permission_level = EXCLUDED.permission_level;

-- Insert permissions and map to roles
DO $$
DECLARE
    v_view_role_id UUID;
    v_standard_role_id UUID;
    v_service_role_id UUID;
    v_admin_role_id UUID;
    v_perm_id UUID;
BEGIN
    -- Get role IDs
    SELECT id INTO v_view_role_id FROM roles WHERE name = 'view_user';
    SELECT id INTO v_standard_role_id FROM roles WHERE name = 'standard_user';
    SELECT id INTO v_service_role_id FROM roles WHERE name = 'service_user';
    SELECT id INTO v_admin_role_id FROM roles WHERE name = 'super_admin';
    
    -- View User Permissions
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'agent.view', 'agent', 'view', 'View agents', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_view_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'agent.view';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_view_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'workflow.view', 'workflow', 'view', 'View workflows', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_view_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'workflow.view';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_view_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    -- Standard User Permissions (includes view)
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'agent.execute', 'agent', 'execute', 'Execute agents', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_standard_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'agent.execute';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_standard_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'workflow.execute', 'workflow', 'execute', 'Execute workflows', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_standard_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'workflow.execute';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_standard_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    -- Service User Permissions (full CRUD)
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'agent.create', 'agent', 'create', 'Create agents', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_service_role_id, v_perm_id) ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'agent.create';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_service_role_id, v_perm_id) ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'agent.manage', 'agent', 'manage', 'Modify/delete agents', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_service_role_id, v_perm_id) ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'agent.manage';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_service_role_id, v_perm_id) ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'workflow.create', 'workflow', 'create', 'Create workflows', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_service_role_id, v_perm_id) ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'workflow.create';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_service_role_id, v_perm_id) ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'workflow.manage', 'workflow', 'manage', 'Modify/delete workflows', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_service_role_id, v_perm_id) ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'workflow.manage';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_service_role_id, v_perm_id) ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    -- Super Admin Permissions (system-wide)
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'user.manage', 'user', 'manage', 'Manage users', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'user.manage';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'role.manage', 'role', 'manage', 'Manage roles and permissions', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'role.manage';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
    
    INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
    VALUES (gen_random_uuid(), 'system.configure', 'system', 'configure', 'Configure system settings', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_perm_id;
    IF v_perm_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    ELSE
        SELECT id INTO v_perm_id FROM permissions WHERE name = 'system.configure';
        INSERT INTO role_permissions (role_id, permission_id) VALUES (v_admin_role_id, v_perm_id) ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- Verify seeding
SELECT 'Roles seeded:' as info;
SELECT name, display_name, permission_level FROM roles ORDER BY permission_level;

SELECT 'Permissions seeded:' as info;
SELECT COUNT(*) as permission_count FROM permissions;

SELECT 'Role-Permission mappings:' as info;
SELECT r.name as role, COUNT(rp.permission_id) as permission_count 
FROM roles r 
LEFT JOIN role_permissions rp ON r.id = rp.role_id 
GROUP BY r.id, r.name 
ORDER BY r.permission_level;
