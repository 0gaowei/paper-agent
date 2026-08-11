import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ApiConfig, SearchConfig, DataSourceConfig } from '@/types'
import { getSettings, saveSettings as apiSaveSettings } from '@/api'

export const useSettingsStore = defineStore('settings', () => {
  const apiConfig = ref<ApiConfig>({
    provider: 'openai',
    apiKey: '',
    baseUrl: '',
    model: 'gpt-4-turbo'
  })

  const searchConfig = ref<SearchConfig>({
    enableQueryDecomposition: true,
    enableIterativeSearch: true,
    enableQueryRewrite: true,
    maxIterations: 3,
    maxResults: 100
  })

  const dataSources = ref<DataSourceConfig[]>([
    { name: 'OpenAlex', enabled: true, priority: 1 }
  ])

  const isLoading = ref(false)
  const isSaving = ref(false)
  const lastSaved = ref<string | null>(null)

  async function loadSettings() {
    isLoading.value = true
    try {
      const settings = await getSettings()
      apiConfig.value = settings.apiConfig
      searchConfig.value = settings.searchConfig
      dataSources.value = settings.dataSources
    } finally {
      isLoading.value = false
    }
  }

  async function saveSettings() {
    isSaving.value = true
    try {
      const settings = {
        apiConfig: apiConfig.value,
        searchConfig: searchConfig.value,
        dataSources: dataSources.value
      }
      await apiSaveSettings(settings)
      lastSaved.value = new Date().toISOString()
    } finally {
      isSaving.value = false
    }
  }

  function updateApiConfig(config: Partial<ApiConfig>) {
    apiConfig.value = { ...apiConfig.value, ...config }
  }

  function updateSearchConfig(config: Partial<SearchConfig>) {
    searchConfig.value = { ...searchConfig.value, ...config }
  }

  function toggleDataSource(name: string) {
    const source = dataSources.value.find(s => s.name === name)
    if (source) {
      source.enabled = !source.enabled
    }
  }

  function updateDataSourcePriority(name: string, priority: number) {
    const source = dataSources.value.find(s => s.name === name)
    if (source) {
      source.priority = priority
    }
  }

  function resetToDefaults() {
    apiConfig.value = {
      provider: 'openai',
      apiKey: '',
      baseUrl: '',
      model: 'gpt-4-turbo'
    }
    searchConfig.value = {
      enableQueryDecomposition: true,
      enableIterativeSearch: true,
      enableQueryRewrite: true,
      maxIterations: 3,
      maxResults: 100
    }
    dataSources.value = [
      { name: 'OpenAlex', enabled: true, priority: 1 }
    ]
  }

  return {
    apiConfig,
    searchConfig,
    dataSources,
    isLoading,
    isSaving,
    lastSaved,
    loadSettings,
    saveSettings,
    updateApiConfig,
    updateSearchConfig,
    toggleDataSource,
    updateDataSourcePriority,
    resetToDefaults
  }
})
