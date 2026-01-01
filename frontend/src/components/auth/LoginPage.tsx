import React, { useState } from 'react'
import { Box, Button, TextField, Typography, Paper, Alert } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const LoginPage = () => {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const { login } = useAuth()
    const navigate = useNavigate()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        try {
            await login({ email, password })
            navigate('/')
        } catch (err: any) {
            // Axios error might be nested
            const msg = err.response?.data?.detail || 'Invalid email or password'
            setError(msg)
        }
    }

    return (
        <Box sx={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'background.default' }}>
            <Paper sx={{ p: 4, width: 400, bgcolor: 'background.paper' }}>
                <Typography variant="h5" sx={{ mb: 3, color: 'text.primary' }}>Login</Typography>
                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
                <form onSubmit={handleSubmit}>
                    <TextField
                        label="Email"
                        fullWidth
                        margin="normal"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />
                    <TextField
                        label="Password"
                        type="password"
                        fullWidth
                        margin="normal"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    <Button type="submit" variant="contained" fullWidth sx={{ mt: 2 }}>
                        Login
                    </Button>
                </form>
            </Paper>
        </Box>
    )
}

export default LoginPage
