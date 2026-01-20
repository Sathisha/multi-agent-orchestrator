import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { NotificationProvider } from './contexts/NotificationContext'
import { MCPProvider } from './contexts/MCPContext'

// Create a dark theme similar to VS Code
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#007acc',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#1e1e1e',
      paper: '#252526',
    },
    text: {
      primary: '#cccccc',
      secondary: '#969696',
    },
  },
  typography: {
    fontFamily: '"Consolas", "Monaco", "Courier New", monospace',
    fontSize: 13,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarColor: '#6b6b6b #2b2b2b',
          '&::-webkit-scrollbar, & *::-webkit-scrollbar': {
            backgroundColor: '#2b2b2b',
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-thumb, & *::-webkit-scrollbar-thumb': {
            borderRadius: 8,
            backgroundColor: '#6b6b6b',
            minHeight: 24,
          },
          '&::-webkit-scrollbar-thumb:focus, & *::-webkit-scrollbar-thumb:focus': {
            backgroundColor: '#959595',
          },
          '&::-webkit-scrollbar-thumb:active, & *::-webkit-scrollbar-thumb:active': {
            backgroundColor: '#959595',
          },
          '&::-webkit-scrollbar-thumb:hover, & *::-webkit-scrollbar-thumb:hover': {
            backgroundColor: '#959595',
          },
          '&::-webkit-scrollbar-corner, & *::-webkit-scrollbar-corner': {
            backgroundColor: '#2b2b2b',
          },
        },
      },
    },
  },
})

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <NotificationProvider>
            <MCPProvider>
              <ThemeProvider theme={darkTheme}>
                <CssBaseline />
                <App />
              </ThemeProvider>
            </MCPProvider>
          </NotificationProvider>
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>,
)