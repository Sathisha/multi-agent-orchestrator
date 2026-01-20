import React, { useState } from 'react'
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Typography,
    Box,
    Tabs,
    Tab,
    Paper,
    TextField,
    Alert,
    IconButton,
    Tooltip
} from '@mui/material'
import { ContentCopy as CopyIcon, Add as AddIcon } from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getAPIKeys, createAPIKey, CreateAPIKeyRequest, CreateAPIKeyResponse } from '../../api/api_keys'
import { login, AuthResponse } from '../../api/auth'
import { Chain } from '../../types/chain'

interface UseAsApiModalProps {
    open: boolean
    onClose: () => void
    chain: Chain
}

interface TabPanelProps {
    children?: React.ReactNode
    index: number
    value: number
}

function TabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props

    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            id={`api-tabpanel-${index}`}
            aria-labelledby={`api-tab-${index}`}
            {...other}
        >
            {value === index && (
                <Box sx={{ p: 2 }}>
                    {children}
                </Box>
            )}
        </div>
    )
}

const UseAsApiModal: React.FC<UseAsApiModalProps> = ({ open, onClose, chain }) => {
    const [tabValue, setTabValue] = useState(0)
    const [newKeyName, setNewKeyName] = useState('')
    const [createdKey, setCreatedKey] = useState<string | null>(null)
    const [authType, setAuthType] = useState<'apikey' | 'jwt'>('apikey')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')

    const [generatedToken, setGeneratedToken] = useState<string | null>(null)
    const [tokenError, setTokenError] = useState<string | null>(null)
    const [executionId, setExecutionId] = useState('')
    const queryClient = useQueryClient()

    const { data: apiKeysData } = useQuery(
        'apiKeys',
        () => getAPIKeys()
    )

    const createKeyMutation = useMutation<CreateAPIKeyResponse, Error, CreateAPIKeyRequest>(createAPIKey, {
        onSuccess: (data: CreateAPIKeyResponse) => {
            setCreatedKey(data.key)
            setNewKeyName('')
            queryClient.invalidateQueries('apiKeys')
        }
    })

    const loginMutation = useMutation<AuthResponse, Error, void>(
        () => login({ email, password }),
        {
            onSuccess: (data) => {
                setGeneratedToken(data.access_token)
                setTokenError(null)
            },
            onError: (error) => {
                setTokenError(error.message || 'Login failed')
            }
        }
    )

    const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabValue(newValue)
    }

    const handleCreateKey = () => {
        if (!newKeyName.trim()) return
        createKeyMutation.mutate({
            name: newKeyName,
            description: `Generated for workflow: ${chain.name}`
        })
    }

    const handleGenerateToken = () => {
        if (!email || !password) return
        loginMutation.mutate()
    }

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text)
    }

    const endpointUrl = `${window.location.protocol}//${window.location.host}/api/v1/chains/${chain.id}/execute`
    const statusUrl = `${window.location.protocol}//${window.location.host}/api/v1/chains/executions/${executionId || '<EXECUTION_ID>'}/status`
    const resultUrl = `${window.location.protocol}//${window.location.host}/api/v1/chains/executions/${executionId || '<EXECUTION_ID>'}`
    const simpleResultUrl = `${window.location.protocol}//${window.location.host}/api/v1/chains/executions/${executionId || '<EXECUTION_ID>'}?view=simple`

    // Auth header logic
    const isJwt = authType === 'jwt'
    const authHeaderName = isJwt ? 'Authorization' : 'X-API-Key'
    const authHeaderValue = isJwt
        ? (generatedToken ? `Bearer ${generatedToken}` : 'Bearer <YOUR_JWT_TOKEN>')
        : (createdKey || (apiKeysData?.api_keys[0] ? apiKeysData.api_keys[0].key_prefix : '<YOUR_API_KEY>'))

    // Code examples
    const curlExample = `curl -X POST "${endpointUrl}" \\
  -H "Content-Type: application/json" \\
  -H "${authHeaderName}: ${authHeaderValue}" \\
  -d '{
    "input_data": {
      "query": "Hello world"
    }
  }'`

    const statusCurlExample = `curl -X GET "${statusUrl}" \\
  -H "${authHeaderName}: ${authHeaderValue}" | python3 -m json.tool`

    const resultCurlExample = `curl -X GET "${resultUrl}" \\
  -H "${authHeaderName}: ${authHeaderValue}" | python3 -m json.tool`

    const simpleResultCurlExample = `curl -X GET "${simpleResultUrl}" \\
  -H "${authHeaderName}: ${authHeaderValue}" | python3 -m json.tool`

    const pythonExample = `import requests

url = "${endpointUrl}"
headers = {
    "Content-Type": "application/json",
    "${authHeaderName}": "${authHeaderValue}"
}
data = {
    "input_data": {
        "query": "Hello world"
    }
}

response = requests.post(url, headers=headers, json=data)
print(response.json())`

    const jsExample = `const url = "${endpointUrl}";
const headers = {
    "Content-Type": "application/json",
    "${authHeaderName}": "${authHeaderValue}"
};
const body = {
    "input_data": {
        "query": "Hello world"
    }
};

fetch(url, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(body)
})
.then(response => response.json())
.then(data => console.log(data));`

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
            <DialogTitle>Use Workflow as API</DialogTitle>
            <DialogContent>
                <Typography variant="body2" color="text.secondary" paragraph>
                    Integrate this workflow into your applications using the API endpoint below.
                    You'll need an API Key for authentication.
                </Typography>

                {/* API Endpoint Section */}
                <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: '#f5f5f5' }}>
                    <Typography variant="subtitle2" gutterBottom>API Endpoint</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, bgcolor: 'white', p: 1.5, borderRadius: 1, border: '1px solid #dee2e6' }}>
                        <Typography sx={{ fontFamily: 'monospace', fontSize: '13px', flexGrow: 1, wordBreak: 'break-all' }}>
                            {endpointUrl}
                        </Typography>
                        <Tooltip title="Copy URL">
                            <IconButton size="small" onClick={() => copyToClipboard(endpointUrl)}>
                                <CopyIcon fontSize="small" />
                            </IconButton>
                        </Tooltip>
                    </Box>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                        POST request to this endpoint to execute the workflow
                    </Typography>
                </Paper>

                {/* Authentication Type Toggle */}
                <Paper variant="outlined" sx={{ p: 2, mb: 3, bgcolor: '#fafafa' }}>
                    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                        <Tabs value={authType} onChange={(e, v) => setAuthType(v)} aria-label="auth type tabs">
                            <Tab label="API Key" value="apikey" />
                            <Tab label="JWT Token" value="jwt" />
                        </Tabs>
                    </Box>

                    {authType === 'apikey' ? (
                        <>
                            <Typography variant="subtitle2" gutterBottom>API Key Management</Typography>
                            {createdKey ? (
                                <Alert severity="success" sx={{ mb: 2 }}>
                                    <Typography variant="body2" fontWeight="bold">New API Key Created!</Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, bgcolor: 'white', p: 1, borderRadius: 1, border: '1px solid #dee2e6' }}>
                                        <Typography sx={{ fontFamily: 'monospace', flexGrow: 1, wordBreak: 'break-all' }}>
                                            {createdKey}
                                        </Typography>
                                        <IconButton size="small" onClick={() => copyToClipboard(createdKey)}>
                                            <CopyIcon fontSize="small" />
                                        </IconButton>
                                    </Box>
                                    <Typography variant="caption" display="block" sx={{ mt: 1, color: 'text.secondary' }}>
                                        Save this key now! You won't be able to see it again.
                                    </Typography>
                                </Alert>
                            ) : (
                                <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                                    <TextField
                                        size="small"
                                        placeholder="New Key Name (e.g. My App)"
                                        value={newKeyName}
                                        onChange={(e) => setNewKeyName(e.target.value)}
                                        sx={{ width: 200 }}
                                    />
                                    <Button
                                        variant="contained"
                                        startIcon={<AddIcon />}
                                        onClick={handleCreateKey}
                                        disabled={!newKeyName.trim() || createKeyMutation.isLoading}
                                    >
                                        Generate Key
                                    </Button>
                                </Box>
                            )}

                            {!createdKey && apiKeysData?.api_keys && apiKeysData.api_keys.length > 0 && (
                                <Box sx={{ mt: 2 }}>
                                    <Typography variant="caption" color="text.secondary">
                                        Existing Keys ({apiKeysData.api_keys.length}):
                                    </Typography>
                                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5 }}>
                                        {apiKeysData.api_keys.slice(0, 3).map(k => (
                                            <Paper key={k.id} variant="outlined" sx={{ px: 1, py: 0.5, bgcolor: 'white', fontSize: '0.75rem' }}>
                                                {k.name} (...{k.key_prefix.slice(-4)})
                                            </Paper>
                                        ))}
                                        {apiKeysData.api_keys.length > 3 && (
                                            <Typography variant="caption" sx={{ alignSelf: 'center' }}>+ {apiKeysData.api_keys.length - 3} more</Typography>
                                        )}
                                    </Box>
                                </Box>
                            )}
                        </>
                    ) : (
                        <>
                            <Typography variant="subtitle2" gutterBottom>Generate Temporary JWT Token</Typography>
                            <Typography variant="caption" color="text.secondary" paragraph>
                                Use your credentials to generate a bearer token for testing. Tokens expire after 30 minutes.
                            </Typography>

                            {generatedToken ? (
                                <Alert severity="success">
                                    <Typography variant="body2" fontWeight="bold">Token Generated!</Typography>
                                    <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                                        The code snippets below have been updated with your token.
                                    </Typography>
                                    <Button
                                        size="small"
                                        sx={{ mt: 1 }}
                                        onClick={() => setGeneratedToken(null)}
                                    >
                                        Generate New Token
                                    </Button>
                                </Alert>
                            ) : (
                                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 400 }}>
                                    {tokenError && <Alert severity="error">{tokenError}</Alert>}
                                    <TextField
                                        label="Email"
                                        size="small"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                    />
                                    <TextField
                                        label="Password"
                                        type="password"
                                        size="small"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                    />
                                    <Button
                                        variant="contained"
                                        onClick={handleGenerateToken}
                                        disabled={!email || !password || loginMutation.isLoading}
                                    >
                                        {loginMutation.isLoading ? 'Generating...' : 'Generate Token'}
                                    </Button>
                                </Box>
                            )}
                        </>
                    )}
                </Paper>

                {/* Integration Tabs */}
                <Typography variant="subtitle2" gutterBottom>Integration Code</Typography>
                <Paper variant="outlined">
                    <Tabs value={tabValue} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
                        <Tab label="cURL" />
                        <Tab label="Python" />
                        <Tab label="JavaScript" />
                    </Tabs>

                    <TabPanel value={tabValue} index={0}>
                        <Box sx={{ mb: 2 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                                <Typography variant="caption" color="text.secondary">Execute Workflow</Typography>
                                <Tooltip title="Copy Code">
                                    <IconButton size="small" onClick={() => copyToClipboard(curlExample)}>
                                        <CopyIcon fontSize="small" />
                                    </IconButton>
                                </Tooltip>
                            </Box>
                            <Box component="pre" sx={{ margin: 0, overflow: 'auto', p: 1.5, bgcolor: '#1e1e1e', color: '#d4d4d4', borderRadius: 1, fontSize: '13px' }}>
                                {curlExample}
                            </Box>
                        </Box>
                        <Box>
                            <Typography variant="subtitle2" sx={{ mb: 1, mt: 3 }}>Check Status</Typography>
                            <Typography variant="caption" color="text.secondary" paragraph>
                                Check the status of a running execution. Paste the Execution ID from the execution response below.
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                                <TextField
                                    size="small"
                                    placeholder="Paste Execution ID here"
                                    value={executionId}
                                    onChange={(e) => setExecutionId(e.target.value)}
                                    fullWidth
                                    sx={{ bgcolor: 'white' }}
                                />
                            </Box>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                                <Typography variant="caption" color="text.secondary">Status Check Command</Typography>
                                <Tooltip title="Copy Code">
                                    <IconButton size="small" onClick={() => copyToClipboard(statusCurlExample)}>
                                        <CopyIcon fontSize="small" />
                                    </IconButton>
                                </Tooltip>
                            </Box>
                            <Box component="pre" sx={{ margin: 0, overflow: 'auto', p: 1.5, bgcolor: '#1e1e1e', color: '#d4d4d4', borderRadius: 1, fontSize: '13px' }}>
                                {statusCurlExample}
                            </Box>

                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5, mt: 3 }}>
                                <Typography variant="caption" color="text.secondary">Get Execution Output</Typography>
                                <Tooltip title="Copy Code">
                                    <IconButton size="small" onClick={() => copyToClipboard(resultCurlExample)}>
                                        <CopyIcon fontSize="small" />
                                    </IconButton>
                                </Tooltip>
                            </Box>
                            <Box component="pre" sx={{ margin: 0, overflow: 'auto', p: 1.5, bgcolor: '#1e1e1e', color: '#d4d4d4', borderRadius: 1, fontSize: '13px' }}>
                                {resultCurlExample}
                            </Box>

                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5, mt: 3 }}>
                                <Typography variant="caption" color="text.secondary">Get Simple Output (JSON)</Typography>
                                <Tooltip title="Copy Code">
                                    <IconButton size="small" onClick={() => copyToClipboard(simpleResultCurlExample)}>
                                        <CopyIcon fontSize="small" />
                                    </IconButton>
                                </Tooltip>
                            </Box>
                            <Box component="pre" sx={{ margin: 0, overflow: 'auto', p: 1.5, bgcolor: '#1e1e1e', color: '#d4d4d4', borderRadius: 1, fontSize: '13px' }}>
                                {simpleResultCurlExample}
                            </Box>
                        </Box>
                    </TabPanel>
                    <TabPanel value={tabValue} index={1}>
                        <Box sx={{ position: 'relative' }}>
                            <Tooltip title="Copy Code">
                                <IconButton
                                    sx={{ position: 'absolute', right: 0, top: -40, zIndex: 1 }}
                                    onClick={() => copyToClipboard(pythonExample)}
                                >
                                    <CopyIcon />
                                </IconButton>
                            </Tooltip>
                            <Box component="pre" sx={{ margin: 0, overflow: 'auto', p: 1.5, bgcolor: '#1e1e1e', color: '#d4d4d4', borderRadius: 1, fontSize: '13px' }}>
                                {pythonExample}
                            </Box>
                        </Box>
                    </TabPanel>
                    <TabPanel value={tabValue} index={2}>
                        <Box sx={{ position: 'relative' }}>
                            <Tooltip title="Copy Code">
                                <IconButton
                                    sx={{ position: 'absolute', right: 0, top: -40, zIndex: 1 }}
                                    onClick={() => copyToClipboard(jsExample)}
                                >
                                    <CopyIcon />
                                </IconButton>
                            </Tooltip>
                            <Box component="pre" sx={{ margin: 0, overflow: 'auto', p: 1.5, bgcolor: '#1e1e1e', color: '#d4d4d4', borderRadius: 1, fontSize: '13px' }}>
                                {jsExample}
                            </Box>
                        </Box>
                    </TabPanel>

                </Paper>

            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Close</Button>
            </DialogActions>
        </Dialog >
    )
}

export default UseAsApiModal
