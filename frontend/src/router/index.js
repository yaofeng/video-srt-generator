import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/upload'
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('../views/UploadView.vue')
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('../views/TasksView.vue')
  },
  {
    path: '/processing/:id',
    name: 'Processing',
    component: () => import('../views/ProcessingView.vue')
  },
  {
    path: '/preview/:id',
    name: 'Preview',
    component: () => import('../views/PreviewView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
