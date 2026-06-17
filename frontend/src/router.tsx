import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from './components/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AdminPage } from './pages/AdminPage';
import { AnalysisTasksPage } from './pages/AnalysisTasksPage';
import { ChatPage } from './pages/ChatPage';
import { DocumentDetailPage } from './pages/DocumentDetailPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { EvidencePackPage } from './pages/EvidencePackPage';
import { LoginPage } from './pages/LoginPage';
import { ProductIdentifyPage } from './pages/ProductIdentifyPage';
import { UploadPage } from './pages/UploadPage';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/documents" replace /> },
      { path: 'documents', element: <DocumentsPage /> },
      { path: 'documents/upload', element: <UploadPage /> },
      { path: 'documents/:id', element: <DocumentDetailPage /> },
      { path: 'products/identify', element: <ProductIdentifyPage /> },
      { path: 'evidence-pack', element: <EvidencePackPage /> },
      { path: 'analysis-tasks', element: <AnalysisTasksPage /> },
      { path: 'chat', element: <ChatPage /> },
      { path: 'admin', element: <AdminPage /> },
    ],
  },
]);
