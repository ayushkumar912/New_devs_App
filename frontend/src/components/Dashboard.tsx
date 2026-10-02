import React, { useEffect, useState } from "react";
import { RevenueSummary } from "./RevenueSummary";
import { SecureAPI } from "../lib/secureApi";

interface DashboardProperty {
  id: string;
  name: string;
}

const Dashboard: React.FC = () => {
  const [properties, setProperties] = useState<DashboardProperty[]>([]);
  const [selectedProperty, setSelectedProperty] = useState('');
  const [propertiesError, setPropertiesError] = useState('');
  const [month, setMonth] = useState(3);
  const [year, setYear] = useState(2024);

  useEffect(() => {
    let cancelled = false;
    SecureAPI.getDashboardProperties()
      .then((data) => {
        if (cancelled) return;
        const rows = data.properties || [];
        setProperties(rows);
        setSelectedProperty((current) => (
          rows.some((property) => property.id === current) ? current : (rows[0]?.id || '')
        ));
      })
      .catch(() => {
        if (!cancelled) setPropertiesError('Failed to load properties');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="p-4 lg:p-6 min-h-full">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-900">Property Management Dashboard</h1>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 lg:p-6">
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
              <div>
                <h2 className="text-lg lg:text-xl font-medium text-gray-900 mb-2">Revenue Overview</h2>
                <p className="text-sm lg:text-base text-gray-600">
                  Monthly performance insights for your properties
                </p>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-gray-700 mb-1" htmlFor="revenue-month">Month</label>
                  <input
                    id="revenue-month"
                    type="number"
                    min={1}
                    max={12}
                    value={month}
                    onChange={(e) => setMonth(Number(e.target.value))}
                    className="block w-full sm:w-24 px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm"
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs font-medium text-gray-700 mb-1" htmlFor="revenue-year">Year</label>
                  <input
                    id="revenue-year"
                    type="number"
                    min={2000}
                    max={2100}
                    value={year}
                    onChange={(e) => setYear(Number(e.target.value))}
                    className="block w-full sm:w-28 px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm"
                  />
                </div>
                <div className="flex flex-col sm:items-end">
                <label className="text-xs font-medium text-gray-700 mb-1">Select Property</label>
                <select
                  value={selectedProperty}
                  onChange={(e) => setSelectedProperty(e.target.value)}
                  className="block w-full sm:w-auto min-w-[200px] px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                >
                  {properties.map((property) => (
                    <option key={property.id} value={property.id}>
                      {property.name}
                    </option>
                  ))}
                </select>
                </div>
              </div>
            </div>
          </div>

          {propertiesError && (
            <div className="p-4 text-red-500 bg-red-50 rounded-lg">{propertiesError}</div>
          )}

          <div className="space-y-6">
            {selectedProperty && (
              <RevenueSummary propertyId={selectedProperty} month={month} year={year} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
