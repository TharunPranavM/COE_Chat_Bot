import React from 'react';
import NavigationBar from '../components/layout/NavigationBar';
import ChatInterface from '../components/user/ChatInterface';

const UserDashboard = () => {
  return (
    <div className="h-screen flex flex-col">
      <NavigationBar />
      <div className="flex-1 overflow-hidden">
        <ChatInterface />
      </div>
    </div>
  );
};

export default UserDashboard;
