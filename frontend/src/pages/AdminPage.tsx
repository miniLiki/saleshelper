import { ReloadOutlined } from '@ant-design/icons';
import { Button, Card, Descriptions, Space, Table, Tag, Typography, message } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { api } from '../services/api';

interface Job {
  id: number;
  document_id?: number | null;
  version_id?: number | null;
  job_type: string;
  status: string;
  error_message?: string | null;
  created_at: string;
}

interface Candidate {
  id: number;
  candidate_type: string;
  payload_json: Record<string, unknown>;
  source_chunk_id?: number | null;
  confidence: number;
  status: string;
  error_message?: string | null;
  created_at: string;
}

export function AdminPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [indexStatus, setIndexStatus] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const [jobsResponse, candidatesResponse] = await Promise.all([
        api.get('/api/admin/ingestion-jobs'),
        api.get('/api/admin/extraction-candidates', { params: { page_size: 50 } }),
      ]);
      setJobs(jobsResponse.data.items);
      setCandidates(candidatesResponse.data.items);
    } catch {
      messageApi.error('任务列表加载失败');
    } finally {
      setLoading(false);
    }
  };

  const confirmCandidate = async (id: number) => {
    await api.post(`/api/admin/extraction-candidates/${id}/confirm`);
    messageApi.success('候选知识已确认');
    fetchJobs();
  };

  const ignoreCandidate = async (id: number) => {
    await api.post(`/api/admin/extraction-candidates/${id}/ignore`);
    messageApi.success('候选知识已忽略');
    fetchJobs();
  };

  const rebuildIndexes = async () => {
    setLoading(true);
    try {
      await api.post('/api/admin/indexes/rebuild');
      messageApi.success('索引重建完成');
      verifyIndexes();
    } catch (error: any) {
      messageApi.error(error.response?.data?.detail || '索引重建失败');
    } finally {
      setLoading(false);
    }
  };

  const verifyIndexes = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/admin/indexes/verify');
      setIndexStatus(response.data);
    } catch (error: any) {
      messageApi.error(error.response?.data?.detail || '索引验证失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    verifyIndexes();
  }, []);

  return (
    <div className="page">
      {contextHolder}
      <div className="page-header">
        <div>
          <Typography.Title level={3}>管理后台</Typography.Title>
          <Typography.Text type="secondary">查看资料接入任务状态</Typography.Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchJobs} />
          <Button onClick={verifyIndexes} loading={loading}>验证索引</Button>
          <Button type="primary" onClick={rebuildIndexes} loading={loading}>重建索引</Button>
        </Space>
      </div>
      {indexStatus && (
        <Card title="索引验证">
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="总体状态">
              <Tag color={indexStatus.status === 'ok' ? 'green' : 'orange'}>{indexStatus.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="PostgreSQL">
              embedded_chunks: {indexStatus.postgres?.embedded_chunks ?? 0}
            </Descriptions.Item>
            <Descriptions.Item label="Milvus">
              <pre className="json-preview">{JSON.stringify(indexStatus.milvus, null, 2)}</pre>
            </Descriptions.Item>
            <Descriptions.Item label="Neo4j">
              <pre className="json-preview">{JSON.stringify(indexStatus.neo4j, null, 2)}</pre>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
      <Card title="接入任务">
        <Table
          rowKey="id"
          loading={loading}
          dataSource={jobs}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 90 },
            { title: '资料 ID', dataIndex: 'document_id' },
            { title: '版本 ID', dataIndex: 'version_id' },
            { title: '类型', dataIndex: 'job_type' },
            { title: '状态', dataIndex: 'status', render: (value: string) => <Tag>{value}</Tag> },
            { title: '错误', dataIndex: 'error_message' },
            { title: '创建时间', dataIndex: 'created_at', render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm') },
          ]}
        />
      </Card>
      <Card title="候选知识" className="result-card">
        <Table
          rowKey="id"
          loading={loading}
          dataSource={candidates}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 80 },
            { title: '类型', dataIndex: 'candidate_type', width: 150 },
            { title: '置信度', dataIndex: 'confidence', width: 100 },
            { title: '状态', dataIndex: 'status', width: 110, render: (value: string) => <Tag>{value}</Tag> },
            { title: '来源 chunk', dataIndex: 'source_chunk_id', width: 120 },
            { title: '内容', dataIndex: 'payload_json', render: (value) => <pre className="json-preview">{JSON.stringify(value, null, 2)}</pre> },
            {
              title: '操作',
              width: 160,
              render: (_, record) => (
                <Space>
                  <Button onClick={() => confirmCandidate(record.id)}>确认</Button>
                  <Button onClick={() => ignoreCandidate(record.id)}>忽略</Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
