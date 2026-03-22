import { View, Text, ScrollView, Input } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useState, useCallback } from 'react'
import { aiModelApi, AIModelConfigItem, CreateAIModelInput } from '@/services/aiModel'
import './index.scss'

export default function AIModelsPage() {
  const [models, setModels] = useState<AIModelConfigItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingModel, setEditingModel] = useState<AIModelConfigItem | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // 表单状态
  const [formData, setFormData] = useState<CreateAIModelInput>({
    display_name: '',
    provider_note: '',
    model_id: '',
    api_key: '',
    base_url: '',
    is_default: false,
  })

  useDidShow(() => {
    loadModels()
  })

  const loadModels = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await aiModelApi.listModels()
      setModels(data)
    } catch (error) {
      console.error('获取模型列表失败:', error)
      Taro.showToast({ title: '获取模型失败', icon: 'none' })
    } finally {
      setIsLoading(false)
    }
  }, [])

  const resetForm = () => {
    setFormData({
      display_name: '',
      provider_note: '',
      model_id: '',
      api_key: '',
      base_url: '',
      is_default: false,
    })
    setEditingModel(null)
    setTestResult(null)
  }

  const openAddModal = () => {
    resetForm()
    setShowAddModal(true)
  }

  const openEditModal = (model: AIModelConfigItem) => {
    setFormData({
      display_name: model.display_name,
      provider_note: model.provider_note || '',
      model_id: model.model_id,
      api_key: '',
      base_url: model.base_url.replace(/\/+$/, '').replace(/\/chat\/completions$/i, ''),
      key: model.key,
      is_default: false,
    })
    setEditingModel(model)
    setTestResult(null)
    setShowAddModal(true)
  }

  const closeModal = () => {
    setShowAddModal(false)
    resetForm()
  }

  const handleTestConnection = async () => {
    if (!formData.model_id || !formData.base_url) {
      setTestResult({ type: 'error', message: '请先填写模型标识和 Base URL' })
      return
    }
    if (!formData.api_key && !editingModel) {
      setTestResult({ type: 'error', message: '请填写 API Key' })
      return
    }

    setIsTesting(true)
    setTestResult(null)
    try {
      const result = await aiModelApi.testConnection({
        provider_note: formData.provider_note || undefined,
        model_id: formData.model_id,
        api_key: formData.api_key || undefined,
        base_url: formData.base_url,
      })
      setTestResult({ type: result.status, message: result.message })
    } catch (error: any) {
      setTestResult({ type: 'error', message: error.message || '测试连接失败' })
    } finally {
      setIsTesting(false)
    }
  }

  const handleSubmit = async () => {
    if (!formData.display_name.trim()) {
      Taro.showToast({ title: '请填写模型名称', icon: 'none' })
      return
    }
    if (!formData.model_id.trim()) {
      Taro.showToast({ title: '请填写模型标识', icon: 'none' })
      return
    }
    if (!formData.base_url.trim()) {
      Taro.showToast({ title: '请填写 Base URL', icon: 'none' })
      return
    }
    if (!editingModel && !formData.api_key?.trim()) {
      Taro.showToast({ title: '新增模型时必须填写 API Key', icon: 'none' })
      return
    }

    setIsSaving(true)
    try {
      const payload: CreateAIModelInput = {
        display_name: formData.display_name.trim(),
        provider_note: formData.provider_note?.trim() || undefined,
        model_id: formData.model_id.trim(),
        api_key: formData.api_key?.trim() || undefined,
        base_url: formData.base_url.trim().replace(/\/+$/, ''),
        key: editingModel?.key,
        is_default: formData.is_default,
      }

      await aiModelApi.createModel(payload)
      Taro.showToast({ title: editingModel ? '更新成功' : '添加成功', icon: 'success' })
      closeModal()
      loadModels()
    } catch (error: any) {
      Taro.showToast({ title: error.message || '操作失败', icon: 'none' })
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (model: AIModelConfigItem) => {
    if (model.is_builtin) {
      Taro.showToast({ title: '系统内置模型不可删除', icon: 'none' })
      return
    }

    const res = await Taro.showModal({
      title: '确认删除',
      content: `确定要删除模型 "${model.display_name}" 吗？`,
      confirmColor: '#ef4444',
    })

    if (res.confirm) {
      try {
        await aiModelApi.deleteModel(model.key)
        Taro.showToast({ title: '已删除', icon: 'success' })
        loadModels()
      } catch (error: any) {
        Taro.showToast({ title: error.message || '删除失败', icon: 'none' })
      }
    }
  }

  return (
    <View className="ai-models-page">
      <View className="header">
        <View className="header-content">
          <Text className="header-title">AI 模型管理</Text>
          <Text className="header-subtitle">{models.length} 个已配置</Text>
        </View>
        <View className="add-btn" onClick={openAddModal}>
          <Text>+ 添加</Text>
        </View>
      </View>

      <ScrollView className="content" scrollY>
        {isLoading ? (
          <View className="loading">
            <View className="loading-spinner" />
            <Text>加载中...</Text>
          </View>
        ) : models.length === 0 ? (
          <View className="empty">
            <Text className="empty-icon">🤖</Text>
            <Text className="empty-text">暂无配置的模型</Text>
            <View className="empty-action" onClick={openAddModal}>
              <Text>添加模型</Text>
            </View>
          </View>
        ) : (
          <View className="model-list">
            {models.map((model) => (
              <View key={model.key} className="model-card">
                <View className="model-header">
                  <View className="model-title-row">
                    <Text className="model-name">{model.display_name}</Text>
                    <View className="model-badges">
                      {model.is_builtin && (
                        <View className="badge builtin">
                          <Text>系统内置</Text>
                        </View>
                      )}
                      <View className={`badge ${model.is_active ? 'active' : 'inactive'}`}>
                        <Text>{model.is_active ? '已启用' : '已停用'}</Text>
                      </View>
                    </View>
                  </View>
                  <Text className="model-provider">
                    {model.provider_note || '未填写提供商'} · {model.model_id}
                  </Text>
                </View>

                <View className="model-info">
                  <View className="info-item">
                    <Text className="info-label">API 密钥:</Text>
                    <Text className="info-value">{model.masked_api_key || (model.has_api_key ? '已保存' : '未保存')}</Text>
                  </View>
                  <View className="info-item">
                    <Text className="info-label">API 地址:</Text>
                    <Text className="info-value url">{model.base_url}</Text>
                  </View>
                </View>

                <View className="model-actions">
                  {!model.is_builtin && (
                    <>
                      <View className="action-btn edit" onClick={() => openEditModal(model)}>
                        <Text>编辑</Text>
                      </View>
                      <View className="action-btn delete" onClick={() => handleDelete(model)}>
                        <Text>删除</Text>
                      </View>
                    </>
                  )}
                </View>
              </View>
            ))}
          </View>
        )}
      </ScrollView>

      {/* 添加/编辑模态框 */}
      {showAddModal && (
        <View className="modal-overlay" onClick={closeModal}>
          <View className="modal-content" onClick={(e) => e.stopPropagation()}>
            <View className="modal-header">
              <Text className="modal-title">{editingModel ? '编辑模型' : '添加新模型'}</Text>
              <View className="modal-close" onClick={closeModal}>
                <Text>×</Text>
              </View>
            </View>

            <ScrollView className="modal-body" scrollY>
              <View className="form-item">
                <Text className="form-label">模型名称 *</Text>
                <Input
                  className="form-input"
                  placeholder="例如：Claude Sonnet 4"
                  value={formData.display_name}
                  onInput={(e) => setFormData((prev) => ({ ...prev, display_name: e.detail.value }))}
                />
              </View>

              <View className="form-item">
                <Text className="form-label">模型标识 *</Text>
                <Input
                  className="form-input"
                  placeholder="例如：gpt-4o-mini / deepseek-r1"
                  value={formData.model_id}
                  onInput={(e) => setFormData((prev) => ({ ...prev, model_id: e.detail.value }))}
                />
              </View>

              <View className="form-item">
                <Text className="form-label">Base URL *</Text>
                <Input
                  className="form-input"
                  placeholder="例如：https://api.openai.com/v1"
                  value={formData.base_url}
                  onInput={(e) => setFormData((prev) => ({ ...prev, base_url: e.detail.value }))}
                />
              </View>

              <View className="form-item">
                <Text className="form-label">API Key {editingModel ? '(留空保留原密钥)' : '*'}</Text>
                <Input
                  className="form-input"
                  password
                  placeholder={editingModel ? '留空则保留当前密钥' : '输入 API Key'}
                  value={formData.api_key}
                  onInput={(e) => setFormData((prev) => ({ ...prev, api_key: e.detail.value }))}
                />
              </View>

              <View className="form-item">
                <Text className="form-label">提供商备注</Text>
                <Input
                  className="form-input"
                  placeholder="例如：OpenRouter / 自建中转"
                  value={formData.provider_note}
                  onInput={(e) => setFormData((prev) => ({ ...prev, provider_note: e.detail.value }))}
                />
              </View>

              <View className="form-item switch-item">
                <View className="switch-info">
                  <Text className="form-label">设为默认模型</Text>
                  <Text className="form-hint">添加后自动设为全站默认 AI 模型</Text>
                </View>
                <View 
                  className={`switch ${formData.is_default ? 'on' : ''}`}
                  onClick={() => setFormData((prev) => ({ ...prev, is_default: !prev.is_default }))}
                >
                  <View className="switch-handle" />
                </View>
              </View>

              {testResult && (
                <View className={`test-result ${testResult.type}`}>
                  <Text>{testResult.message}</Text>
                </View>
              )}
            </ScrollView>

            <View className="modal-footer">
              <View className="btn outline" onClick={handleTestConnection}>
                <Text>{isTesting ? '测试中...' : '测试连接'}</Text>
              </View>
              <View className={`btn primary ${isSaving ? 'disabled' : ''}`} onClick={handleSubmit}>
                <Text>{isSaving ? '保存中...' : (editingModel ? '保存修改' : '添加模型')}</Text>
              </View>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
