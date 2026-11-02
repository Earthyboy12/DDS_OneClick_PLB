import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { FilterBar } from './components/FilterBar';
import { SyntheticBanner } from './components/SyntheticBanner';
import { ImportPage } from './pages/ImportPage';
import { OverviewPage } from './pages/OverviewPage';
import { TimePage } from './pages/TimePage';
import { DistrictsPage } from './pages/DistrictsPage';
import { PersonRatesPage } from './pages/PersonRatesPage';
import { SummaryTablesPage } from './pages/SummaryTablesPage';
import { ForecastPage } from './pages/ForecastPage';
import { PresentationStudioPage } from './pages/PresentationStudioPage';
import { MethodsExportPage } from './pages/MethodsExportPage';

class PageErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; errorMsg: string }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, errorMsg: '' };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, errorMsg: error?.message || String(error) };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('PageErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 bg-white rounded-2xl border border-rose-200 max-w-xl mx-auto my-8 text-center space-y-3 shadow-xs">
          <h3 className="text-lg font-bold text-rose-800">เกิดข้อผิดพลาดในการแสดงผลหน้านี้</h3>
          <p className="text-xs text-slate-600 font-mono bg-slate-50 p-3 rounded-xl border border-slate-200">
            {this.state.errorMsg}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, errorMsg: '' })}
            className="px-4 py-2 rounded-xl bg-teal-700 text-white text-xs font-semibold"
          >
            ลองโหลดหน้านี้ใหม่
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const PageContent: React.FC = () => {
  const { activeTab } = useApp();

  const getPageTitles = () => {
    switch (activeTab) {
      case 'import':
        return { th: '1. นำเข้าหลายไฟล์ (.xlsx / .csv) และตรวจสอบข้อมูล', en: '1. Multi-File Import (.xlsx / .csv) & Data Quality' };
      case 'overview':
        return { th: '2. ภาพรวมระบาดวิทยา (Epidemiological Overview)', en: '2. Epidemiological Overview' };
      case 'time':
        return { th: '3. แนวโน้มการระบาดตามเวลา (Time Trends & Epicurve)', en: '3. Surveillance Time Trends (Time)' };
      case 'districts':
        return { th: '4. การกระจายทางภูมิศาสตร์รายอำเภอ (Place & Districts)', en: '4. Geographical District Analysis (Place)' };
      case 'person':
        return { th: '5. บุคคลและอัตราป่วยตามกลุ่มอายุ (Person & Rates)', en: '5. Person Characteristics & Population Rates (Person)' };
      case 'tables':
        return { th: '6. ตารางสรุปมาตรฐานระบาดวิทยา (ตารางที่ 0–4)', en: '6. Standard Surveillance Summary Tables (Tables 0–4)' };
      case 'forecast':
        return { th: '7. การพยากรณ์จำนวนผู้ป่วยรายสัปดาห์ (Weekly OLS Forecast <=52 Weeks)', en: '7. Weekly OLS Epidemiological Forecasting (<=52 Weeks)' };
      case 'studio':
        return { th: '8. ห้องจัดสไลด์ระดับ 4K (Figure 1–7 ภาษาไทย/อังกฤษ)', en: '8. 4K Slide Presentation Studio (Figures 1–7 TH/EN)' };
      case 'methods':
        return { th: '9. ระเบียบวิธีทางสถิติและการส่งออกข้อมูล (Methods & Export)', en: '9. Methodology & Data Export' };
      default:
        return { th: 'DDS One-Click Surveillance', en: 'DDS One-Click Surveillance' };
    }
  };

  const titles = getPageTitles();

  const renderActivePage = () => {
    switch (activeTab) {
      case 'import':
        return <ImportPage />;
      case 'overview':
        return <OverviewPage />;
      case 'time':
        return <TimePage />;
      case 'districts':
        return <DistrictsPage />;
      case 'person':
        return <PersonRatesPage />;
      case 'tables':
        return <SummaryTablesPage />;
      case 'forecast':
        return <ForecastPage />;
      case 'studio':
        return <PresentationStudioPage />;
      case 'methods':
        return <MethodsExportPage />;
      default:
        return <ImportPage />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <SyntheticBanner />
        <Header titleTh={titles.th} titleEn={titles.en} />
        <FilterBar />

        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="max-w-[1440px] mx-auto">
            <PageErrorBoundary key={activeTab}>
              {renderActivePage()}
            </PageErrorBoundary>
          </div>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AppProvider>
      <PageContent />
    </AppProvider>
  );
};

export default App;
