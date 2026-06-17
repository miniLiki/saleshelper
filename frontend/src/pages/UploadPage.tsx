import { InboxOutlined } from '@ant-design/icons';
import { Button, Form, Input, InputNumber, Select, Typography, Upload, message } from 'antd';
import type { UploadFile } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

export function UploadPage() {
  const navigate = useNavigate();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const onFinish = async (values: Record<string, string | number>) => {
    if (!fileList[0]?.originFileObj) {
      messageApi.error('请选择要上传的文件');
      return;
    }
    const formData = new FormData();
    formData.append('file', fileList[0].originFileObj);
    Object.entries(values).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        formData.append(key, String(value));
      }
    });
    setSubmitting(true);
    try {
      await api.post('/api/documents', formData);
      messageApi.success('资料上传成功');
      navigate('/documents');
    } catch (error: any) {
      messageApi.error(error.response?.data?.detail || '资料上传失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page narrow-page">
      {contextHolder}
      <Typography.Title level={3}>上传资料</Typography.Title>
      <Form
        layout="vertical"
        onFinish={onFinish}
        initialValues={{ trust_level: 3, permission_scope: 'internal' }}
      >
        <Form.Item label="文件" required>
          <Upload.Dragger
            beforeUpload={() => false}
            maxCount={1}
            fileList={fileList}
            onChange={({ fileList: nextFileList }) => setFileList(nextFileList)}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p>点击或拖拽文件到此处</p>
          </Upload.Dragger>
        </Form.Item>
        <Form.Item name="title" label="资料标题" rules={[{ required: true, message: '请输入资料标题' }]}>
          <Input />
        </Form.Item>
        <Form.Item name="file_type" label="文件类型" rules={[{ required: true, message: '请选择文件类型' }]}>
          <Select options={['pdf', 'word', 'excel', 'ppt', 'markdown', 'txt'].map((value) => ({ value, label: value }))} />
        </Form.Item>
        <Form.Item name="business_type" label="资料类型" rules={[{ required: true, message: '请选择资料类型' }]}>
          <Select options={[
            { value: 'product_material', label: '产品资料' },
            { value: 'customer_case', label: '客户案例' },
            { value: 'industry_material', label: '行业资料' },
            { value: 'competitor_material', label: '竞品资料' },
            { value: 'sales_faq', label: '销售 FAQ' },
          ]} />
        </Form.Item>
        <Form.Item name="source_type" label="来源类型" rules={[{ required: true, message: '请输入来源类型' }]}>
          <Input placeholder="internal_product_doc / competitor_official / industry_report" />
        </Form.Item>
        <Form.Item name="trust_level" label="可信等级" rules={[{ required: true }]}>
          <InputNumber min={1} max={5} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="permission_scope" label="权限范围" rules={[{ required: true }]}>
          <Select options={[
            { value: 'internal', label: '内部' },
            { value: 'restricted', label: '受限' },
            { value: 'public', label: '公开' },
          ]} />
        </Form.Item>
        <Form.Item name="product_id" label="产品 ID"><Input /></Form.Item>
        <Form.Item name="competitor_id" label="竞品 ID"><Input /></Form.Item>
        <Form.Item name="industry_id" label="行业 ID"><Input /></Form.Item>
        <Button type="primary" htmlType="submit" loading={submitting}>提交</Button>
      </Form>
    </div>
  );
}
