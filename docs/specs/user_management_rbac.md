# User Management and Role-Based Access Control (RBAC) Specification

This document defines the comprehensive user management, role assignment, and role-based access control (RBAC) system for the Multi-Agent Orchestrator platform. It establishes the permissions model, user-role mapping, and access control mechanisms for agents and workflows.

## 1. Objective

To implement a secure, granular, and enterprise-grade access control system that:
- **Manages users**: Create, update, and delete users with proper authentication.
- **Defines roles**: Establish a standard set of roles with clearly defined permissions.
- **Controls access**: Enforce role-based permissions for agents, workflows, and system resources.
- **Enables multi-user collaboration**: Allow teams to work together while maintaining security boundaries.
- **Maintains audit trails**: Track all user actions and permission changes for compliance.

## 2. Role Definitions

The system defines three primary roles with distinct permission levels:

### 2.1 View User

**Permission Level**: Read-Only
**Description**: Limited access for users who need visibility but should not interact with or modify resources.

**Allowed Actions**:
- View list of all agents
- View agent details (name, description, configuration)
- View list of all workflows
- View workflow details (structure, nodes, edges)
- View execution history (read-only)
- View execution logs (read-only)
- Access dashboard and analytics (read-only)

**Restricted Actions**:
- ❌ Cannot create, modify, or delete agents
- ❌ Cannot execute agents or workflows
- ❌ Cannot create, modify, or delete workflows
- ❌ Cannot access user management features
- ❌ Cannot modify any system configuration

### 2.2 Standard User

**Permission Level**: Execute
**Description**: Interactive users who can execute existing agents and workflows but cannot modify them.

**Allowed Actions**:
- All permissions of View User, PLUS:
- Execute agents (test/chat with agents)
- Execute workflows (trigger workflow runs)
- View their own execution results
- Create and manage personal API keys
- View role assignments (their own)

**Restricted Actions**:
- ❌ Cannot create, modify, or delete agents
- ❌ Cannot create, modify, or delete workflows
- ❌ Cannot delete execution history or logs
- ❌ Cannot access user management features
- ❌ Cannot modify role assignments

### 2.3 Service User

**Permission Level**: Full Control
**Description**: Administrators, developers, and service accounts with full system access.

**Allowed Actions**:
- All permissions of Standard User, PLUS:
- Create new agents
- Modify existing agents (configuration, tools, prompts)
- Delete agents
- Create new workflows
- Modify existing workflows (add/remove nodes, update edges)
- Delete workflows
- Assign roles to agents
- Assign roles to workflows
- Manage LLM models and configurations
- Delete execution history and logs
- Access system configuration

**Restricted Actions**:
- ❌ Cannot manage users (create/delete users) - Reserved for Super Admin
- ❌ Cannot modify role definitions - Reserved for Super Admin

### 2.4 Super Admin (System-Level)

**Permission Level**: System Administrator
**Description**: System-level administrators with complete control over users, roles, and system configuration.

**Allowed Actions**:
- All permissions of Service User, PLUS:
- Create, modify, and delete users
- Assign and revoke roles from users
- Manage role definitions and permissions
- Access all system-level configurations
- View all audit trails and security logs
- Configure authentication and security settings
- Manage API rate limits and quotas

## 3. Data Model

### 3.1 User Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    
    -- Indexes
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_is_active (is_active)
);
```

### 3.2 Role Table

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    permission_level INTEGER NOT NULL, -- 1=View, 2=Execute, 3=Modify
    is_system_role BOOLEAN DEFAULT false, -- Cannot be deleted
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_name (name),
    INDEX idx_permission_level (permission_level)
);
```

**Default Roles** (seeded during system initialization):
```sql
INSERT INTO roles (name, display_name, permission_level, is_system_role) VALUES
('view_user', 'View User', 1, true),
('standard_user', 'Standard User', 2, true),
('service_user', 'Service User', 3, true),
('super_admin', 'Super Administrator', 4, true);
```

### 3.3 User-Role Association Table

```sql
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(id), -- Who granted this role
    assigned_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP, -- Optional expiration for temporary access
    
    -- Composite unique constraint
    UNIQUE(user_id, role_id),
    
    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_role_id (role_id)
);
```

### 3.4 Agent-Role Association Table

```sql
CREATE TABLE agent_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    access_type VARCHAR(50) NOT NULL, -- 'execute', 'modify', 'view'
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Composite unique constraint
    UNIQUE(agent_id, role_id, access_type),
    
    -- Indexes
    INDEX idx_agent_id (agent_id),
    INDEX idx_role_id (role_id)
);
```

### 3.5 Workflow-Role Association Table

```sql
CREATE TABLE workflow_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES chains(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    access_type VARCHAR(50) NOT NULL, -- 'execute', 'modify', 'view'
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Composite unique constraint
    UNIQUE(workflow_id, role_id, access_type),
    
    -- Indexes
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_role_id (role_id)
);
```

### 3.6 Audit Log Enhancements

Add user context to existing audit logs:

```sql
ALTER TABLE audit_logs ADD COLUMN user_id UUID REFERENCES users(id);
ALTER TABLE audit_logs ADD COLUMN role_id UUID REFERENCES roles(id);
ALTER TABLE audit_logs ADD INDEX idx_user_id (user_id);
```

## 4. Permission Enforcement Logic

### 4.1 Permission Check Algorithm

```python
def has_permission(user: User, resource: Resource, action: str) -> bool:
    """
    Check if a user has permission to perform an action on a resource.
    
    Args:
        user: The user attempting the action
        resource: The resource being accessed (Agent, Workflow, etc.)
        action: The action being attempted ('view', 'execute', 'modify', 'delete')
    
    Returns:
        bool: True if permission is granted, False otherwise
    """
    # Super admins have all permissions
    if user.is_superuser:
        return True
    
    # Get user's roles
    user_roles = get_user_roles(user.id)
    
    # Check resource-specific permissions
    resource_roles = get_resource_roles(resource.id, resource.type)
    
    # Map action to minimum required permission level
    action_permission_map = {
        'view': 1,      # View User or higher
        'execute': 2,   # Standard User or higher
        'modify': 3,    # Service User or higher
        'delete': 3     # Service User or higher
    }
    
    required_level = action_permission_map.get(action, 3)
    
    # Check if user has any role that meets the requirement
    for user_role in user_roles:
        if user_role.permission_level >= required_level:
            # Check if this role has access to the specific resource
            for resource_role in resource_roles:
                if resource_role.id == user_role.id:
                    # Check access type matches
                    if is_access_type_sufficient(resource_role.access_type, action):
                        return True
    
    return False

def is_access_type_sufficient(granted_access: str, requested_action: str) -> bool:
    """Check if granted access type is sufficient for requested action."""
    access_hierarchy = {
        'view': ['view'],
        'execute': ['view', 'execute'],
        'modify': ['view', 'execute', 'modify']
    }
    return requested_action in access_hierarchy.get(granted_access, [])
```

### 4.2 Resource Access Matrix

| Resource Type | View User | Standard User | Service User |
|---------------|-----------|---------------|--------------|
| Agent - List | ✅ | ✅ | ✅ |
| Agent - View Details | ✅ (if assigned) | ✅ (if assigned) | ✅ |
| Agent - Execute | ❌ | ✅ (if assigned) | ✅ |
| Agent - Create | ❌ | ❌ | ✅ |
| Agent - Modify | ❌ | ❌ | ✅ (if assigned) |
| Agent - Delete | ❌ | ❌ | ✅ (if assigned) |
| Workflow - List | ✅ | ✅ | ✅ |
| Workflow - View Details | ✅ (if assigned) | ✅ (if assigned) | ✅ |
| Workflow - Execute | ❌ | ✅ (if assigned) | ✅ |
| Workflow - Create | ❌ | ❌ | ✅ |
| Workflow - Modify | ❌ | ❌ | ✅ (if assigned) |
| Workflow - Delete | ❌ | ❌ | ✅ (if assigned) |
| User - List | ❌ | ❌ | ❌ (Super Admin only) |
| User - Create | ❌ | ❌ | ❌ (Super Admin only) |
| User - Modify Roles | ❌ | ❌ | ❌ (Super Admin only) |

## 5. API Endpoints

### 5.1 User Management

#### Create User
```
POST /api/v1/users
Authorization: Bearer <super_admin_token>

Request Body:
{
    "username": "john.doe",
    "email": "john.doe@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe",
    "role_ids": ["<role_uuid>"]
}

Response: 201 Created
{
    "id": "<user_uuid>",
    "username": "john.doe",
    "email": "john.doe@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "roles": [
        {
            "id": "<role_uuid>",
            "name": "standard_user",
            "display_name": "Standard User"
        }
    ],
    "created_at": "2024-01-17T15:30:00Z"
}
```

#### List Users
```
GET /api/v1/users?page=1&size=20&role=standard_user
Authorization: Bearer <super_admin_token>

Response: 200 OK
{
    "users": [
        {
            "id": "<user_uuid>",
            "username": "john.doe",
            "email": "john.doe@example.com",
            "full_name": "John Doe",
            "is_active": true,
            "roles": [...],
            "last_login": "2024-01-17T15:00:00Z"
        }
    ],
    "total": 50,
    "page": 1,
    "size": 20
}
```

#### Update User
```
PATCH /api/v1/users/<user_id>
Authorization: Bearer <super_admin_token>

Request Body:
{
    "full_name": "John Updated Doe",
    "is_active": false
}

Response: 200 OK
```

#### Delete User
```
DELETE /api/v1/users/<user_id>
Authorization: Bearer <super_admin_token>

Response: 204 No Content
```

### 5.2 Role Management

#### Assign Role to User
```
POST /api/v1/users/<user_id>/roles
Authorization: Bearer <super_admin_token>

Request Body:
{
    "role_id": "<role_uuid>",
    "expires_at": "2024-12-31T23:59:59Z" // Optional
}

Response: 201 Created
```

#### Revoke Role from User
```
DELETE /api/v1/users/<user_id>/roles/<role_id>
Authorization: Bearer <super_admin_token>

Response: 204 No Content
```

#### List All Roles
```
GET /api/v1/roles
Authorization: Bearer <token>

Response: 200 OK
{
    "roles": [
        {
            "id": "<role_uuid>",
            "name": "view_user",
            "display_name": "View User",
            "description": "Can only view agents and workflows",
            "permission_level": 1,
            "is_system_role": true
        }
    ]
}
```

### 5.3 Agent Role Assignment

#### Assign Role to Agent
```
POST /api/v1/agents/<agent_id>/roles
Authorization: Bearer <service_user_token>

Request Body:
{
    "role_id": "<role_uuid>",
    "access_type": "execute" // 'view', 'execute', or 'modify'
}

Response: 201 Created
{
    "id": "<assignment_uuid>",
    "agent_id": "<agent_uuid>",
    "role_id": "<role_uuid>",
    "access_type": "execute",
    "created_at": "2024-01-17T15:30:00Z"
}
```

#### List Agent Roles
```
GET /api/v1/agents/<agent_id>/roles
Authorization: Bearer <token>

Response: 200 OK
{
    "agent_id": "<agent_uuid>",
    "roles": [
        {
            "role_id": "<role_uuid>",
            "role_name": "standard_user",
            "access_type": "execute"
        }
    ]
}
```

#### Remove Role from Agent
```
DELETE /api/v1/agents/<agent_id>/roles/<role_id>
Authorization: Bearer <service_user_token>

Response: 204 No Content
```

### 5.4 Workflow Role Assignment

#### Assign Role to Workflow
```
POST /api/v1/workflows/<workflow_id>/roles
Authorization: Bearer <service_user_token>

Request Body:
{
    "role_id": "<role_uuid>",
    "access_type": "execute" // 'view', 'execute', or 'modify'
}

Response: 201 Created
```

#### List Workflow Roles
```
GET /api/v1/workflows/<workflow_id>/roles
Authorization: Bearer <token>

Response: 200 OK
{
    "workflow_id": "<workflow_uuid>",
    "roles": [
        {
            "role_id": "<role_uuid>",
            "role_name": "standard_user",
            "access_type": "execute"
        }
    ]
}
```

#### Remove Role from Workflow
```
DELETE /api/v1/workflows/<workflow_id>/roles/<role_id>
Authorization: Bearer <service_user_token>

Response: 204 No Content
```

### 5.5 Authentication

#### Login
```
POST /api/v1/auth/login

Request Body:
{
    "username": "john.doe",
    "password": "SecurePassword123!"
}

Response: 200 OK
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
        "id": "<user_uuid>",
        "username": "john.doe",
        "email": "john.doe@example.com",
        "roles": [...]
    }
}
```

#### Logout
```
POST /api/v1/auth/logout
Authorization: Bearer <token>

Response: 204 No Content
```

#### Refresh Token
```
POST /api/v1/auth/refresh

Request Body:
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

Response: 200 OK
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

## 6. Frontend Integration

### 6.1 User Management UI

**Location**: `/users` (Admin only)

**Features**:
- User list with search, filter, and pagination
- Create user dialog with role selection
- Edit user dialog (update name, email, activate/deactivate)
- Delete user confirmation dialog
- Assign/revoke roles inline or via dialog

**Components**:
- `UserManagement.tsx` - Main page
- `UserList.tsx` - User table
- `UserForm.tsx` - Create/Edit form
- `RoleAssignment.tsx` - Role assignment dialog

### 6.2 Agent Creation/Edit UI Enhancement

**Location**: `/agents` (Create/Edit dialogs)

**New Section**: "Access Control"

**Fields**:
- Role selector (multi-select)
- Access type per role (view/execute/modify)
- Visual indicator for inherited permissions

**Example UI**:
```
┌─────────────────────────────────────┐
│ Access Control                      │
├─────────────────────────────────────┤
│ Assign Roles:                       │
│ ☑ View User        [View ▼]         │
│ ☑ Standard User    [Execute ▼]      │
│ ☐ Service User     [Modify ▼]       │
│                                     │
│ ℹ Users with assigned roles can    │
│   access this agent based on their │
│   permission level.                │
└─────────────────────────────────────┘
```

### 6.3 Workflow Creation/Edit UI Enhancement

**Location**: `/workflows` (Create/Edit dialogs)

**New Section**: "Access Control" (identical to agents)

### 6.4 Navigation Changes

**Admin Menu** (visible only to Super Admin):
```
- Users
  - User Management
  - Role Management
```

**Profile Menu** (all users):
```
- My Profile
- My Roles
- API Keys
- Logout
```

### 6.5 Permission-Based UI Rendering

**Conditional Rendering Examples**:
```typescript
// Hide "Create Agent" button for non-Service Users
{hasPermission('agent', 'create') && (
    <Button onClick={handleCreateAgent}>Create Agent</Button>
)}

// Disable "Execute" button if user lacks permission
<Button 
    onClick={handleExecute}
    disabled={!hasPermission('agent', 'execute', agentId)}
>
    Execute
</Button>

// Show read-only view for View Users
{userRole === 'view_user' ? (
    <ViewOnlyAgentDetails agent={agent} />
) : (
    <EditableAgentDetails agent={agent} />
)}
```

### 6.6 Authentication State Management

**Context**: `AuthContext.tsx`

**State**:
```typescript
interface AuthState {
    user: User | null;
    roles: Role[];
    permissions: Permission[];
    isAuthenticated: boolean;
    isLoading: boolean;
}
```

**Methods**:
```typescript
interface AuthContextType {
    login: (username: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    hasPermission: (resource: string, action: string, resourceId?: string) => boolean;
    hasRole: (roleName: string) => boolean;
}
```

## 7. Backend Implementation

### 7.1 Service Layer

**UserService** (`app/services/user_service.py`):
- `create_user(user_data: UserCreate) -> User`
- `get_user_by_id(user_id: UUID) -> User`
- `get_users(filters: UserFilters, pagination: Pagination) -> List[User]`
- `update_user(user_id: UUID, user_data: UserUpdate) -> User`
- `delete_user(user_id: UUID) -> None`
- `assign_role(user_id: UUID, role_id: UUID) -> UserRole`
- `revoke_role(user_id: UUID, role_id: UUID) -> None`

**RoleService** (`app/services/role_service.py`):
- `get_all_roles() -> List[Role]`
- `get_role_by_id(role_id: UUID) -> Role`
- `create_role(role_data: RoleCreate) -> Role` (Super Admin only)

**PermissionService** (`app/services/permission_service.py`):
- `has_permission(user: User, resource_type: str, action: str, resource_id: UUID = None) -> bool`
- `get_user_permissions(user_id: UUID) -> List[Permission]`
- `assign_resource_role(resource_type: str, resource_id: UUID, role_id: UUID, access_type: str) -> ResourceRole`
- `revoke_resource_role(resource_type: str, resource_id: UUID, role_id: UUID) -> None`

**AuthService** (`app/services/auth_service.py`):
- `authenticate(username: str, password: str) -> TokenPair`
- `verify_token(token: str) -> User`
- `refresh_access_token(refresh_token: str) -> str`
- `logout(token: str) -> None`

### 7.2 Middleware and Decorators

**Authentication Middleware** (`app/middleware/auth.py`):
```python
async def authenticate_request(request: Request) -> User:
    """Extract and verify JWT token from request headers."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await auth_service.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    request.state.user = user
    return user
```

**Permission Decorator** (`app/decorators/permissions.py`):
```python
def require_permission(resource_type: str, action: str):
    """Decorator to enforce permission checks on endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request') or args[0]
            user = request.state.user
            
            # Extract resource_id from path parameters if present
            resource_id = kwargs.get(f'{resource_type}_id')
            
            if not permission_service.has_permission(
                user, resource_type, action, resource_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions to {action} {resource_type}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

**Usage Example**:
```python
@router.post("/agents/{agent_id}/execute")
@require_permission("agent", "execute")
async def execute_agent(
    agent_id: UUID,
    request: Request,
    payload: ExecuteRequest
):
    user = request.state.user
    # ... execute agent logic
```

### 7.3 Database Migrations

**Migration 001**: Create User and Role tables
```bash
make migration MESSAGE="create_user_and_role_tables"
```

**Migration 002**: Create User-Role association table
```bash
make migration MESSAGE="create_user_role_association"
```

**Migration 003**: Create Agent-Role and Workflow-Role association tables
```bash
make migration MESSAGE="create_resource_role_associations"
```

**Migration 004**: Seed default roles
```bash
make migration MESSAGE="seed_default_roles"
```

**Migration 005**: Add user_id to audit_logs
```bash
make migration MESSAGE="add_user_to_audit_logs"
```

### 7.4 Authentication Configuration

**JWT Configuration** (`.env`):
```env
# JWT Settings
JWT_SECRET_KEY=<generate-strong-random-secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Hashing
PASSWORD_HASH_ALGORITHM=bcrypt
PASSWORD_MIN_LENGTH=8
```

**Password Requirements**:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

## 8. Security Considerations

### 8.1 Password Security

- Use bcrypt with minimum 12 rounds for password hashing
- Implement rate limiting on login attempts (5 attempts per 15 minutes)
- Enforce password complexity requirements
- Implement password reset flow with email verification
- Store password reset tokens with expiration

### 8.2 Token Security

- Use short-lived access tokens (1 hour)
- Use longer-lived refresh tokens (7 days) stored securely
- Implement token revocation on logout
- Store tokens in httpOnly cookies (frontend) or secure storage
- Implement CSRF protection for cookie-based auth

### 8.3 Authorization Security

- Always verify user permissions server-side (never trust client)
- Use parameterized queries to prevent SQL injection
- Implement row-level security for multi-user access
- Log all permission denials for security auditing
- Implement rate limiting on sensitive endpoints

### 8.4 Audit Trail

Log all significant user actions:
- User login/logout
- Role assignments/revocations
- Resource creation/modification/deletion
- Permission denial events
- Failed authentication attempts

**Audit Log Entry Example**:
```json
{
    "timestamp": "2024-01-17T15:30:00Z",
    "user_id": "<user_uuid>",
    "action": "assign_role",
    "resource_type": "agent",
    "resource_id": "<agent_uuid>",
    "details": {
        "role_id": "<role_uuid>",
        "access_type": "execute"
    },
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
}
```

## 9. Testing Strategy

### 9.1 Unit Tests

**User Management**:
- Test user creation with valid/invalid data
- Test password hashing and verification
- Test role assignment and revocation
- Test user deletion and cascading effects

**Permission Checks**:
- Test permission checks for each role
- Test resource-specific permission checks
- Test permission inheritance
- Test edge cases (expired roles, inactive users)

**Authentication**:
- Test login with valid/invalid credentials
- Test token generation and verification
- Test token refresh flow
- Test logout and token revocation

### 9.2 Integration Tests

**E2E User Flows**:
- Super Admin creates user → assigns role → user logs in
- Service User creates agent → assigns role → Standard User executes
- Standard User attempts to modify agent → denied
- View User attempts to execute workflow → denied

**API Tests**:
- Test all user management endpoints
- Test all role assignment endpoints
- Test authentication flows
- Test permission enforcement on protected endpoints

### 9.3 Security Tests

- Test SQL injection prevention
- Test XSS prevention in user inputs
- Test CSRF protection
- Test rate limiting enforcement
- Test token expiration and refresh
- Test concurrent session handling

## 10. Migration and Deployment

### 10.1 Data Seeding

**Default Super Admin** (first deployment only):
```sql
-- Create default super admin user
INSERT INTO users (username, email, password_hash, full_name, is_superuser) VALUES
('admin', 'admin@example.com', '<bcrypt_hash_of_default_password>', 'System Administrator', true);

-- Assign super_admin role
INSERT INTO user_roles (user_id, role_id) 
SELECT u.id, r.id 
FROM users u, roles r 
WHERE u.username = 'admin' AND r.name = 'super_admin';
```

**IMPORTANT**: Force password change on first login!

### 10.2 Backward Compatibility

For systems already in production without user management:

**Phase 1**: Deploy tables and services
- Create new tables via migrations
- Deploy new API endpoints (disabled by default)
- Keep existing functionality working

**Phase 2**: Enable authentication
- Set environment variable `ENABLE_RBAC=true`
- Create default super admin via CLI command
- Existing functionality continues without auth checks

**Phase 3**: Enforce permissions
- Set environment variable `ENFORCE_RBAC=true`
- All API calls now require authentication
- Migration script to assign all existing agents/workflows to Service User role

### 10.3 CLI Commands

```bash
# Create super admin user
make shell
python -m app.cli.create_superuser --username admin --email admin@example.com

# Migrate existing resources to RBAC
python -m app.cli.migrate_rbac --assign-role service_user

# List all users
python -m app.cli.list_users

# Assign role to user
python -m app.cli.assign_role --user john.doe --role standard_user
```

## 11. Future Enhancements

### 11.1 Advanced Features (Phase 2)

- **Custom Roles**: Allow Service Users to create custom roles with granular permissions
- **Team-Based Access**: Group users into teams with shared access
- **Resource Ownership**: Automatic permission grant to resource creators
- **Permission Delegation**: Users can delegate their permissions temporarily
- **API Key Management**: Generate and manage API keys for programmatic access

### 11.2 Integration Enhancements

- **SSO Integration**: Support for SAML, OAuth2, LDAP
- **MFA Support**: Two-factor authentication via TOTP or SMS
- **Session Management**: View and revoke active sessions
- **Password Policies**: Configurable password expiration and history

### 11.3 Audit and Compliance

- **Detailed Audit Reports**: Downloadable compliance reports
- **Real-Time Alerts**: Notify admins of suspicious activities
- **Data Retention Policies**: Automatic cleanup of old audit logs
- **GDPR Compliance**: User data export and deletion workflows

## 12. Implementation Checklist

### Backend Tasks

- [ ] Create database migrations for all new tables
- [ ] Implement User, Role, and Permission models
- [ ] Implement UserService with CRUD operations
- [ ] Implement RoleService
- [ ] Implement PermissionService with permission check logic
- [ ] Implement AuthService with JWT authentication
- [ ] Create authentication middleware
- [ ] Create permission decorator
- [ ] Add user context to all API endpoints
- [ ] Implement all user management endpoints
- [ ] Implement role assignment endpoints for users
- [ ] Implement role assignment endpoints for agents
- [ ] Implement role assignment endpoints for workflows
- [ ] Add permission checks to existing agent endpoints
- [ ] Add permission checks to existing workflow endpoints
- [ ] Update audit logging to include user context
- [ ] Create CLI commands for user management
- [ ] Seed default roles
- [ ] Create default super admin user
- [ ] Write unit tests for all services
- [ ] Write integration tests for all endpoints
- [ ] Write security tests

### Frontend Tasks

- [ ] Create AuthContext for authentication state
- [ ] Implement login page
- [ ] Implement logout functionality
- [ ] Implement token refresh logic
- [ ] Create UserManagement page (Super Admin only)
- [ ] Create UserList component
- [ ] Create UserForm component (Create/Edit)
- [ ] Create RoleAssignment component
- [ ] Add "Access Control" section to Agent Create/Edit dialog
- [ ] Add "Access Control" section to Workflow Create/Edit dialog
- [ ] Implement permission-based UI rendering
- [ ] Add role badges to user profile
- [ ] Create "My Profile" page
- [ ] Add "Users" menu item (Admin only)
- [ ] Update navigation based on user roles
- [ ] Add loading states for authentication
- [ ] Handle authentication errors gracefully
- [ ] Implement auto-redirect to login on token expiration
- [ ] Write E2E tests for user flows
- [ ] Update documentation

### Documentation Tasks

- [ ] Update API documentation with new endpoints
- [ ] Create user guide for User Management
- [ ] Create admin guide for RBAC setup
- [ ] Update deployment guide with RBAC migration steps
- [ ] Document environment variables
- [ ] Create troubleshooting guide
- [ ] Update README with authentication details

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-17  
**Status**: Draft - Awaiting Review
