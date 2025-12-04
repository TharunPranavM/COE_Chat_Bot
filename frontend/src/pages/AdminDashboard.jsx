import React, { useState } from 'react';
import NavigationBar from '../components/layout/NavigationBar';
import FileUpload from '../components/admin/FileUpload';
import DashboardStats from '../components/admin/DashboardStats';

const AdminDashboard = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadSuccess = () => {
    // Trigger refresh of dashboard stats
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <NavigationBar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <FileUpload onUploadSuccess={handleUploadSuccess} />
          <DashboardStats refreshTrigger={refreshTrigger} />
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
