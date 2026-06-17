import { Button, Descriptions, Empty, Space, Table, Tag, Typography, message } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import type { DocumentDetail } from '../types/api';

export function DocumentDetailPage() {
  const { id } = useParams();
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [messageApi, contextHolder] = message.useMessage();

  const fetchDetail = () => {
    api.get<DocumentDetail>(`/api/documents/${id}`)
      .then((response) => setDetail(response.data))
      .catch(() => messageApi.error('资料详情加载失败'));
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  const processDocument = async () => {
    try {
      await api.post(`/api/documents/${id}/process`);
      messageApi.success('处理任务已完成');
      fetchDetail();
    } catch (error: any) {
      messageApi.error(error.response?.data?.detail || '处理失败');
    }
  };

  if (!detail) {
    return <div className="page">{contextHolder}<Empty description="暂无资料详情" /></div>;
  }

  return (
    <div className="page">
      {contextHolder}
      <div className="page-header">
        <Typography.Title level={3}>{detail.title}</Typography.Title>
        <Space>
          <Button type="primary" onClick={processDocument}>解析/抽取/索引</Button>
        </Space>
      </div>
      <Descriptions bordered column={2}>
        <Descriptions.Item label="文件名">{detail.file_name}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag>{detail.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="资料类型">{detail.business_type}</Descriptions.Item>
        <Descriptions.Item label="文件类型">{detail.file_type}</Descriptions.Item>
        <Descriptions.Item label="可信等级">L{detail.trust_level}</Descriptions.Item>
        <Descriptions.Item label="对象路径">{detail.storage_path}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{dayjs(detail.created_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
        <Descriptions.Item label="更新时间">{dayjs(detail.updated_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
      </Descriptions>
      <Typography.Title level={4}>版本</Typography.Title>
      <Table rowKey="id" dataSource={detail.versions} pagination={false} columns={[
        { title: '版本', dataIndex: 'version' },
        { title: '文件名', dataIndex: 'file_name' },
        { title: '大小', dataIndex: 'file_size' },
        { title: '校验值', dataIndex: 'checksum', ellipsis: true },
      ]} />
      <Typography.Title level={4}>任务</Typography.Title>
      <Table rowKey="id" dataSource={detail.ingestion_jobs} pagination={false} columns={[
        { title: '类型', dataIndex: 'job_type' },
        { title: '状态', dataIndex: 'status' },
        { title: '错误', dataIndex: 'error_message' },
        { title: '创建时间', dataIndex: 'created_at', render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm') },
      ]} />
      <Typography.Title level={4}>Chunks</Typography.Title>
      <Table rowKey="id" dataSource={detail.chunks} pagination={{ pageSize: 5 }} columns={[
        { title: '序号', dataIndex: 'chunk_index', width: 80 },
        { title: '标题路径', dataIndex: 'title_path', width: 180 },
        { title: '页码', dataIndex: 'page_number', width: 80 },
        { title: 'Sheet', dataIndex: 'sheet_name', width: 120 },
        { title: '向量状态', dataIndex: 'vector_status', width: 110, render: (value: string) => <Tag>{value}</Tag> },
        { title: '内容', dataIndex: 'content', ellipsis: true },
      ]} />
    </div>
  );
}
