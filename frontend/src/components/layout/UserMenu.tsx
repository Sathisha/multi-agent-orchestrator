import React, { useState } from 'react'
import { Box, IconButton, Menu, MenuItem, Typography, Divider, Avatar } from '@mui/material'
import { AccountCircle, Logout, Settings } from '@mui/icons-material'
import { useAuth } from '../../context/AuthContext'
import { useNavigate } from 'react-router-dom'

const UserMenu: React.FC = () => {
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
    const { user, logout } = useAuth()
    const navigate = useNavigate()
    const open = Boolean(anchorEl)

    const handleClick = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorEl(event.currentTarget)
    }

    const handleClose = () => {
        setAnchorEl(null)
    }

    const handleLogout = async () => {
        handleClose()
        await logout()
        navigate('/login')
    }

    const getInitials = (name?: string) => {
        if (!name) return 'U'
        return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    }

    return (
        <Box>
            <IconButton
                onClick={handleClick}
                size="small"
                sx={{
                    ml: 1,
                    '&:hover': {
                        backgroundColor: 'rgba(255, 255, 255, 0.1)'
                    }
                }}
                aria-controls={open ? 'user-menu' : undefined}
                aria-haspopup="true"
                aria-expanded={open ? 'true' : undefined}
            >
                <Avatar
                    sx={{
                        width: 28,
                        height: 28,
                        bgcolor: '#007acc',
                        fontSize: '12px',
                        fontWeight: 'bold'
                    }}
                >
                    {getInitials(user?.full_name)}
                </Avatar>
            </IconButton>
            <Menu
                anchorEl={anchorEl}
                id="user-menu"
                open={open}
                onClose={handleClose}
                onClick={handleClose}
                PaperProps={{
                    elevation: 0,
                    sx: {
                        overflow: 'visible',
                        filter: 'drop-shadow(0px 2px 8px rgba(0,0,0,0.32))',
                        mt: 1.5,
                        bgcolor: '#252526',
                        color: '#cccccc',
                        border: '1px solid #2d2d30',
                        '& .MuiAvatar-root': {
                            width: 32,
                            height: 32,
                            ml: -0.5,
                            mr: 1,
                        },
                    },
                }}
                transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            >
                <Box sx={{ px: 2, py: 1.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: '#cccccc' }}>
                        {user?.full_name || 'User'}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#969696' }}>
                        {user?.email}
                    </Typography>
                </Box>
                <Divider sx={{ borderColor: '#2d2d30' }} />
                <MenuItem
                    onClick={handleClose}
                    sx={{
                        '&:hover': {
                            bgcolor: '#2a2d2e'
                        }
                    }}
                >
                    <Settings fontSize="small" sx={{ mr: 1 }} />
                    Settings
                </MenuItem>
                <MenuItem
                    onClick={handleLogout}
                    sx={{
                        color: '#f48771',
                        '&:hover': {
                            bgcolor: '#2a2d2e'
                        }
                    }}
                >
                    <Logout fontSize="small" sx={{ mr: 1 }} />
                    Logout
                </MenuItem>
            </Menu>
        </Box>
    )
}

export default UserMenu
