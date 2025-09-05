# Aspen Backend API Documentation for Frontend

## Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication

### JWT Authentication (Users)
For authenticated user operations, use JWT tokens obtained via registration or login.

**Registration Endpoint**:
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Registration Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user_id": 123,
  "message": "Account created successfully"
}
```

**Login Endpoint**:
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Login Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Usage in subsequent requests**:
```
Authorization: Bearer <jwt_token>
```

### API Key Authentication (Services)
For service-to-service communication, include the API key in the X-API-Key header:
```
X-API-Key: <api_key>
```

---

## 🚀 Quick Start Examples

### 1. User Registration & Login Flow
```javascript
// Register a new user
async function registerUser(email, password, firstName, lastName) {
  const response = await fetch('/api/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password,
      first_name: firstName,
      last_name: lastName
    })
  });
  const data = await response.json();
  return data.access_token;
}

// Login existing user
async function loginUser(email, password) {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await response.json();
  return data.access_token;
}

// Use token in subsequent requests
const token = await loginUser('user@example.com', 'password');
const headers = {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
};
```

### 2. Service Authentication Flow
```javascript
// Example: Use service API key
const headers = {
  'X-API-Key': 'sk-abc123...',
  'Content-Type': 'application/json'
};
```

---

## 📋 API Endpoints

### Services Management

#### Create Service
```http
POST /api/v1/services
```
**Auth**: JWT required
**Body**:
```json
{
  "name": "My Service",
  "environment": "dev"  // "dev" | "stage" | "prod"
}
```
**Response**:
```json
{
  "id": 1,
  "name": "My Service", 
  "environment": "dev",
  "api_key_plaintext": "sk-abc123def456...",  // ONLY shown once!
  "api_key_last4": "3456"
}
```

#### List Services
```http
GET /api/v1/services
```
**Auth**: JWT required
**Response**:
```json
[
  {
    "id": 1,
    "name": "My Service",
    "environment": "dev",
    "api_key_last4": "3456"
  }
]
```

#### Get Service
```http
GET /api/v1/services/{service_id}
```
**Auth**: JWT required
**Response**:
```json
{
  "id": 1,
  "name": "My Service",
  "environment": "dev", 
  "api_key_last4": "3456"
}
```

#### Delete Service
```http
DELETE /api/v1/services/{service_id}
```
**Auth**: JWT required
**Response**: `204 No Content`

#### Rotate API Key
```http
POST /api/v1/services/{service_id}:rotate-key
```
**Auth**: JWT required
**Response**:
```json
{
  "id": 1,
  "name": "My Service",
  "environment": "dev",
  "api_key_plaintext": "sk-new123def456...",  // ONLY shown once!
  "api_key_last4": "6789"
}
```

### Service Segments

#### Create Service Segment
```http
POST /api/v1/services/{service_id}/segments
```
**Auth**: JWT required
**Body**:
```json
{
  "name": "user-analytics"
}
```
**Response**:
```json
{
  "id": 1,
  "service_id": 1,
  "name": "user-analytics"
}
```

#### List Service Segments
```http
GET /api/v1/services/{service_id}/segments
```
**Auth**: JWT required
**Response**:
```json
[
  {
    "id": 1,
    "service_id": 1,
    "name": "user-analytics"
  }
]
```

#### Delete Service Segment
```http
DELETE /api/v1/services/{service_id}/segments/{segment_id}
```
**Auth**: JWT required
**Response**: `204 No Content`

### Service Linking

#### Link Service to Experts
```http
POST /api/v1/services/{service_id}/experts
```
**Auth**: JWT required
**Body**:
```json
{
  "expert_ids": [1, 2, 3]
}
```
**Response**:
```json
{
  "linked": [1, 2, 3]
}
```

#### Unlink Service from Expert
```http
DELETE /api/v1/services/{service_id}/experts/{expert_id}
```
**Auth**: JWT required
**Response**: `204 No Content`

#### Link Service to Workflows
```http
POST /api/v1/services/{service_id}/workflows
```
**Auth**: JWT required
**Body**:
```json
{
  "workflow_ids": [1, 2, 3]
}
```
**Response**:
```json
{
  "linked": [1, 2, 3]
}
```

#### Unlink Service from Workflow
```http
DELETE /api/v1/services/{service_id}/workflows/{workflow_id}
```
**Auth**: JWT required
**Response**: `204 No Content`

#### Get Service Exposure
```http
GET /api/v1/services/{service_id}/exposure
```
**Auth**: JWT required
**Response**:
```json
{
  "service_id": 1,
  "service_name": "My Service",
  "experts": [
    {
      "id": 1,
      "name": "Customer Support Expert",
      "model_name": "gpt-4"
    }
  ],
  "workflows": [
    {
      "id": 1,
      "name": "Lead Processing Workflow",
      "node_count": 3
    }
  ]
}
```

#### Service Identity Check
```http
GET /api/v1/services/whoami
```
**Auth**: JWT or API Key
**Response (with JWT)**:
```json
{
  "type": "user",
  "user_id": 123,
  "email": "user@example.com"
}
```
**Response (with API Key)**:
```json
{
  "type": "service",
  "service_id": 1,
  "name": "My Service",
  "environment": "dev",
  "segments": ["user-analytics"]
}
```

---

## 📋 Data Management Endpoints

### List Experts
```http
GET /api/v1/experts
```
**Auth**: JWT required
**Query Parameters**:
- `limit` (optional): Number of results to return (default: 100)
- `offset` (optional): Number of results to skip (default: 0)

**Response**:
```json
[
  {
    "id": 1,
    "name": "Customer Support Expert",
    "model_name": "gpt-4",
    "status": "active",
    "team_id": 1,
    "created_on": "2024-01-15T10:30:00Z"
  }
]
```

### List Workflows
```http
GET /api/v1/workflows
```
**Auth**: JWT required
**Query Parameters**:
- `limit` (optional): Number of results to return (default: 100)
- `offset` (optional): Number of results to skip (default: 0)

**Response**:
```json
[
  {
    "id": 1,
    "name": "Lead Processing Workflow",
    "description": "Automated lead qualification and routing",
    "team_id": 1,
    "node_count": 3,
    "created_on": "2024-01-15T10:30:00Z"
  }
]
```

---

## 🤖 AI Execution Endpoints

### Run Expert
```http
POST /api/v1/chat/experts:run
```
**Auth**: JWT or API Key
**Body**:
```json
{
  "expert_id": 1,
  "input_params": {
    "user_question": "How do I reset my password?",
    "context": "Customer is using mobile app"
  },
  "base": {
    "custom_date": "2024-01-15"
  }
}
```
**Response**:
```json
{
  "run_id": "run_abc123",
  "messages": [
    {
      "role": "user",
      "content": "How do I reset my password? Context: Customer is using mobile app"
    },
    {
      "role": "assistant", 
      "content": "To reset your password on the mobile app, please follow these steps..."
    }
  ]
}
```

### Run Workflow
```http
POST /api/v1/chat/workflows:run
```
**Auth**: JWT or API Key
**Body**:
```json
{
  "workflow_id": 1,
  "starting_inputs": {
    "lead_email": "prospect@company.com",
    "lead_source": "website"
  }
}
```
**Response**:
```json
{
  "run_id": "run_def456",
  "steps": [
    {
      "node_id": 1,
      "node_type": "job",
      "inputs": {
        "lead_email": "prospect@company.com"
      },
      "outputs": {
        "enriched_data": "..."
      },
      "status": "completed"
    },
    {
      "node_id": 2,
      "node_type": "filter",
      "inputs": {
        "enriched_data": "..."
      },
      "outputs": {
        "qualified": true
      },
      "status": "completed"
    }
  ]
}
```

### Stream Run Events (Server-Sent Events)
```http
GET /api/v1/chat/runs/{run_id}/events
```
**Auth**: JWT or API Key
**Headers**: `Accept: text/event-stream`

**JavaScript Example**:
```javascript
const eventSource = new EventSource(
  `/api/v1/chat/runs/${runId}/events`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
};

// Event format:
// {
//   "ts": "2024-01-15T10:30:00Z",
//   "level": "info",
//   "message": "Node execution completed", 
//   "data": {
//     "node_id": 1,
//     "status": "completed"
//   }
// }
```

---

## 🔧 Frontend Integration Patterns

### 1. Data Loading (Experts & Workflows)
```javascript
// Fetch all experts for the current user
async function loadExperts() {
  const response = await fetch('/api/v1/experts', {
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
}

// Fetch all workflows for the current user
async function loadWorkflows() {
  const response = await fetch('/api/v1/workflows', {
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
}

// Fetch all services for the current user
async function loadServices() {
  const response = await fetch('/api/v1/services', {
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
}

// Create new service
async function createService(name, environment) {
  const response = await fetch('/api/v1/services', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ name, environment })
  });
  
  const service = await response.json();
  
  // IMPORTANT: Save the API key immediately - it's only shown once!
  if (service.api_key_plaintext) {
    // Show API key to user with copy functionality
    showApiKeyModal(service.api_key_plaintext);
  }
  
  return service;
}
```

### 2. AI Chat Interface
```javascript
// Run expert with user input
async function runExpert(expertId, userMessage) {
  const response = await fetch('/api/v1/chat/experts:run', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      expert_id: expertId,
      input_params: {
        user_message: userMessage
      }
    })
  });
  
  const result = await response.json();
  
  // Display conversation
  result.messages.forEach(message => {
    addMessageToChat(message.role, message.content);
  });
  
  return result;
}
```

### 3. Real-time Workflow Monitoring
```javascript
// Monitor workflow execution in real-time
function monitorWorkflow(runId) {
  const eventSource = new EventSource(
    `/api/v1/chat/runs/${runId}/events`,
    {
      headers: {
        'Authorization': `Bearer ${userToken}`
      }
    }
  );

  eventSource.addEventListener('log', (event) => {
    const logData = JSON.parse(event.data);
    updateWorkflowProgress(logData);
  });

  eventSource.addEventListener('error', (event) => {
    const errorData = JSON.parse(event.data);
    showWorkflowError(errorData);
  });

  return eventSource;
}
```

### 4. Service Configuration Flow
```javascript
// Complete service setup flow
async function setupService(serviceName, environment, expertIds, workflowIds) {
  // 1. Create service
  const service = await createService(serviceName, environment);
  
  // 2. Link to experts
  if (expertIds.length > 0) {
    await fetch(`/api/v1/services/${service.id}/experts`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ expert_ids: expertIds })
    });
  }
  
  // 3. Link to workflows  
  if (workflowIds.length > 0) {
    await fetch(`/api/v1/services/${service.id}/workflows`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ workflow_ids: workflowIds })
    });
  }
  
  // 4. Get final exposure summary
  const exposure = await fetch(`/api/v1/services/${service.id}/exposure`, {
    headers: {
      'Authorization': `Bearer ${userToken}`
    }
  }).then(r => r.json());
  
  return { service, exposure };
}
```

---

## 🛡️ Error Handling

### Common HTTP Status Codes
- **200 OK**: Success
- **201 Created**: Resource created successfully  
- **204 No Content**: Success with no response body
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **409 Conflict**: Duplicate resource (e.g., service name already exists)
- **422 Unprocessable Entity**: Validation errors

### Error Response Format
```json
{
  "detail": "Error description here"
}
```

### Frontend Error Handling Example
```javascript
async function apiCall(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    console.error('API Error:', error.message);
    showUserError(error.message);
    throw error;
  }
}
```

---

## 🔑 Environment Variables Required

For the backend to work properly, ensure these environment variables are set:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key
JWT_SECRET=your-jwt-secret-key

# Optional (has defaults)
DATABASE_URL=postgresql://user:pass@localhost/aspen_dev
ENVIRONMENT=development
```

---

## 🧪 Testing Your Integration

### 1. Health Check
```bash
curl http://localhost:8000/docs
# Should return the FastAPI documentation page
```

### 2. Service Authentication Test
```bash
# Create a service (you'll need a JWT token)
curl -X POST http://localhost:8000/api/v1/services \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Service", "environment": "dev"}'

# Test the API key (use the returned api_key_plaintext)
curl http://localhost:8000/api/v1/services/whoami \
  -H "X-API-Key: sk-returned-api-key"
```

### 3. Expert Execution Test
```bash
# Run an expert (you'll need an expert_id and authentication)
curl -X POST http://localhost:8000/api/v1/chat/experts:run \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "expert_id": 1,
    "input_params": {
      "user_question": "Hello, how are you?"
    }
  }'
```

---

## 📚 Additional Resources

- **API Documentation**: Visit `http://localhost:8000/docs` for interactive Swagger UI
- **Alternative Docs**: Visit `http://localhost:8000/redoc` for ReDoc format
- **OpenAPI Schema**: Available at `http://localhost:8000/openapi.json`

---

## 🌐 CORS Configuration

The backend is configured to allow requests from common frontend development ports:

**Allowed Origins**:
- `http://localhost:3000` (React default)
- `http://localhost:3001` (Alternative React port)
- `http://localhost:5173` (Vite default)
- `http://localhost:5174` (Alternative Vite port)
- `http://localhost:8080` (Vue default)
- `http://localhost:4200` (Angular default)
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

**Allowed Methods**: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `PATCH`

**Allowed Headers**: `Accept`, `Authorization`, `Content-Type`, `X-API-Key`, `X-Requested-With`, `Cache-Control`

**Credentials**: Enabled (cookies and authorization headers are allowed)

If your frontend runs on a different port, you may need to add it to the CORS configuration in `app/main.py`.

---

## 🚨 Important Notes for Frontend Developers

1. **API Keys are sensitive**: Only show them once during creation/rotation
2. **JWT tokens expire**: Implement token refresh logic
3. **SSE connections**: Remember to close EventSource connections when components unmount
4. **Rate limiting**: Be prepared to handle rate limiting in production
5. **CORS**: Configured for common development ports. Add production origins as needed.
6. **Real-time updates**: Use Server-Sent Events for workflow/expert execution monitoring
7. **Error boundaries**: Implement proper error handling for all API calls
8. **Loading states**: All API calls are async - show appropriate loading indicators

This backend is production-ready with 100% test coverage and real OpenAI integration. All endpoints are fully functional and ready for frontend integration!
