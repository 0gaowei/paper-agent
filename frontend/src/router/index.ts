import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Search',
    component: () => import('@/views/SearchView.vue')
  },
  {
    path: '/results/:sessionId',
    name: 'Results',
    component: () => import('@/views/ResultsView.vue'),
    props: true
  },
  {
    path: '/paper/:paperId',
    name: 'PaperDetail',
    component: () => import('@/views/PaperDetailView.vue'),
    props: true
  },
  {
    path: '/graph/:sessionId',
    name: 'Graph',
    component: () => import('@/views/GraphView.vue'),
    props: true
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/HistoryView.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue')
  }
]

const router = createRouter({
  history: createWebHistory('/'),
  routes
})

export default router
