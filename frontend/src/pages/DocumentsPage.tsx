import { EyeOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons';
import { Button, Form, Input, Select, Space, Table, Tag, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { DocumentItem, DocumentListResponse } from '../types/api';

const trustColor = ['default', 'red', 'orange', 'gold', 'blue', 'green'];

export function DocumentsPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<DocumentListResponse>({ items: [], total: 0, page: 1, page_size: 20 });
  const [messageApi, contextHolder] = message.useMessage();

  const fetchDocuments = async (page = 1) => {
    setLoading(true);
    try {
      const params = { page, page_size: 20, ...form.getFieldsValue() };
      const response = await api.get<DocumentListResponse>('/api/documents', { params });
      setData(response.data);
    } catch {
      messageApi.error('资料列表加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const columns: ColumnsType<DocumentItem> = [
    { title: '标题', dataIndex: 'title', fixed: 'left' },
    { title: '文件名', dataIndex: 'file_name' },
    { title: '资料类型', dataIndex: 'business_type' },
    { title: '文件类型', dataIndex: 'file_type', width: 96 },
    {
      title: '可信等级',
      dataIndex: 'trust_level',
      width: 110,
      render: (level: number) => <Tag color={trustColor[level]}>L{level}</Tag>,
    },
    { title: '产品', dataIndex: 'product_id', width: 120 },
    { title: '竞品', dataIndex: 'competitor_id', width: 120 },
    { title: '行业', dataIndex: 'industry_id', width: 120 },
    { title: '状态', dataIndex: 'status', width: 110, render: (status: string) => <Tag>{status}</Tag> },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      width: 96,
      render: (_, record) => (
        <Button icon={<EyeOutlined />} onClick={() => navigate(`/documents/${record.id}`)} />
      ),
    },
  ];

  return (
    <div className="page">
      {contextHolder}
      <div className="page-header">
        <div>
          <Typography.Title level={3}>资料管理</Typography.Title>
          <Typography.Text type="secondary">查看上传资料、筛选元数据和跟踪状态</Typography.Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => fetchDocuments(data.page)} />
          <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate('/documents/upload')}>上传资料</Button>
        </Space>
      </div>
      <Form form={form} layout="inline" className="filter-bar" onFinish={() => fetchDocuments()}>
        <Form.Item name="business_type">
          <Select placeholder="资料类型" allowClear style={{ width: 160 }} options={[
            { value: 'product_material', label: '产品资料' },
            { value: 'customer_case', label: '客户案例' },
            { value: 'industry_material', label: '行业资料' },
            { value: 'competitor_material', label: '竞品资料' },
            { value: 'sales_faq', label: '销售 FAQ' },
          ]} />
        </Form.Item>
        <Form.Item name="file_type"><Input placeholder="文件类型" /></Form.Item>
        <Form.Item name="product_id"><Input placeholder="产品 ID" /></Form.Item>
        <Form.Item name="competitor_id"><Input placeholder="竞品 ID" /></Form.Item>
        <Form.Item name="industry_id"><Input placeholder="行业 ID" /></Form.Item>
        <Form.Item name="trust_level">
          <Select placeholder="可信等级" allowClear style={{ width: 120 }} options={[1, 2, 3, 4, 5].map((value) => ({ value, label: `L${value}` }))} />
        </Form.Item>
        <Button type="primary" htmlType="submit">筛选</Button>
      </Form>
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={data.items}
        scroll={{ x: 1200 }}
        pagination={{
          total: data.total,
          current: data.page,
          pageSize: data.page_size,
          onChange: fetchDocuments,
        }}
      />
    </div>
  );
}
