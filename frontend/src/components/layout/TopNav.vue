<template>
  <header class="top-nav">
    <div class="nav-container">
      <div class="nav-left">
        <router-link to="/" class="logo">
          <el-icon class="logo-icon"><Document /></el-icon>
          <span class="logo-text">学术搜索</span>
        </router-link>
      </div>
      
      <nav class="nav-menu">
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
          <el-icon><Search /></el-icon>
          <span>搜索</span>
        </router-link>
        <router-link to="/history" class="nav-item" :class="{ active: $route.path === '/history' }">
          <el-icon><Clock /></el-icon>
          <span>历史</span>
        </router-link>
        <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </router-link>
      </nav>
      
      <div class="nav-right">
        <el-button circle @click="toggleDark">
          {{ isDark ? '☀️' : '🌙' }}
        </el-button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { Document, Search, Clock, Setting } from '@element-plus/icons-vue'
import { ref } from 'vue'

const isDark = ref(false)

const toggleDark = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
}
</script>

<style lang="scss" scoped>
.top-nav {
  background: linear-gradient(135deg, #409EFF 0%, #53a8ff 100%);
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.3);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-left {
  .logo {
    display: flex;
    align-items: center;
    gap: 8px;
    color: white;
    font-size: 20px;
    font-weight: 600;
    text-decoration: none;
    
    .logo-icon {
      font-size: 28px;
    }
    
    &:hover {
      opacity: 0.9;
    }
  }
}

.nav-menu {
  display: flex;
  gap: 8px;
  
  .nav-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 20px;
    color: rgba(255, 255, 255, 0.85);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.3s ease;
    
    &:hover {
      background: rgba(255, 255, 255, 0.2);
      color: white;
    }
    
    &.active {
      background: rgba(255, 255, 255, 0.25);
      color: white;
    }
  }
}

.nav-right {
  :deep(.el-button) {
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    
    &:hover {
      background: rgba(255, 255, 255, 0.3);
    }
  }
}
</style>
