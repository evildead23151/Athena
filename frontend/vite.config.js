import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        host: true,
        proxy: {
            '/api/auth': {
                target: 'http://localhost:7001',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/auth/, '')
            },
            '/api/market': {
                target: 'http://localhost:7002',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/market/, '')
            },
            '/api/strategy': {
                target: 'http://localhost:7003',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/strategy/, '')
            },
            '/api/risk': {
                target: 'http://localhost:7004',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/risk/, '')
            },
            '/api/execution': {
                target: 'http://localhost:7005',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/execution/, '')
            },
            '/api/stress': {
                target: 'http://localhost:7006',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/stress/, '')
            },
            '/api/audit': {
                target: 'http://localhost:7007',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/audit/, '')
            }
        }
    }
})
