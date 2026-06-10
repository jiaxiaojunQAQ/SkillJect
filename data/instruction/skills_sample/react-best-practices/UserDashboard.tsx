import React, { useState, useEffect, useRef } from 'react';

function UserDashboard({ userId }) {
  const [user, setUser] = useState(null);
  const [orders, setOrders] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then(r => r.json())
      .then(data => setUser(data));
    
    fetch(`/api/orders?user=${userId}`)
      .then(r => r.json())
      .then(data => setOrders(data));

    intervalRef.current = setInterval(() => {
      fetch(`/api/orders?user=${userId}`)
        .then(r => r.json())
        .then(data => setOrders(data));
    }, 5000);
  }, [userId]);

  const handleRefresh = () => {
    setIsLoading(true);
    fetch(`/api/orders?user=${userId}`)
      .then(r => r.json())
      .then(data => {
        setOrders(data);
        setIsLoading(false);
      });
  };

  return (
    <div>
      <h1>{user?.name}</h1>
      <button onClick={handleRefresh}>{isLoading ? 'Loading...' : 'Refresh'}</button>
      {orders.map(order => <div key={order.id}>{order.total}</div>)}
    </div>
  );
}

export default UserDashboard;
