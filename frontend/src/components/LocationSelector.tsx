'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Search, MapPin, ChevronDown, X, Loader2 } from 'lucide-react';

// Indian States with major cities
const INDIA_DATA: Record<string, string[]> = {
  'Maharashtra': ['Mumbai', 'Pune', 'Nagpur', 'Nashik', 'Aurangabad', 'Solapur', 'Kolhapur', 'Sangli', 'Thane', 'Navi Mumbai', 'Amravati', 'Akola', 'Latur', 'Nanded', 'Ahmednagar'],
  'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Bhavnagar', 'Jamnagar', 'Gandhinagar', 'Junagadh', 'Anand', 'Nadiad'],
  'Karnataka': ['Bangalore', 'Mysore', 'Hubli', 'Mangalore', 'Belgaum', 'Gulbarga', 'Davangere', 'Bellary', 'Shimoga', 'Tumkur'],
  'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem', 'Tirunelveli', 'Erode', 'Vellore', 'Thoothukudi', 'Dindigul'],
  'Telangana': ['Hyderabad', 'Warangal', 'Nizamabad', 'Karimnagar', 'Khammam', 'Ramagundam', 'Mahbubnagar'],
  'Andhra Pradesh': ['Visakhapatnam', 'Vijayawada', 'Guntur', 'Nellore', 'Kurnool', 'Rajahmundry', 'Tirupati', 'Kakinada', 'Kadapa', 'Anantapur'],
  'Delhi': ['New Delhi', 'Delhi'],
  'Uttar Pradesh': ['Lucknow', 'Kanpur', 'Agra', 'Varanasi', 'Allahabad', 'Ghaziabad', 'Noida', 'Meerut', 'Bareilly', 'Aligarh', 'Moradabad', 'Saharanpur', 'Gorakhpur'],
  'West Bengal': ['Kolkata', 'Howrah', 'Durgapur', 'Asansol', 'Siliguri', 'Bardhaman', 'Malda', 'Baharampur', 'Kharagpur'],
  'Rajasthan': ['Jaipur', 'Jodhpur', 'Udaipur', 'Kota', 'Bikaner', 'Ajmer', 'Bhilwara', 'Alwar', 'Sikar', 'Bharatpur'],
  'Madhya Pradesh': ['Indore', 'Bhopal', 'Jabalpur', 'Gwalior', 'Ujjain', 'Sagar', 'Dewas', 'Satna', 'Ratlam', 'Rewa'],
  'Bihar': ['Patna', 'Gaya', 'Bhagalpur', 'Muzaffarpur', 'Darbhanga', 'Purnia', 'Bihar Sharif', 'Arrah', 'Begusarai'],
  'Odisha': ['Bhubaneswar', 'Cuttack', 'Rourkela', 'Berhampur', 'Sambalpur', 'Puri', 'Balasore', 'Bhadrak'],
  'Kerala': ['Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Thrissur', 'Kollam', 'Kannur', 'Alappuzha', 'Palakkad', 'Malappuram'],
  'Punjab': ['Ludhiana', 'Amritsar', 'Jalandhar', 'Patiala', 'Bathinda', 'Mohali', 'Hoshiarpur', 'Pathankot'],
  'Haryana': ['Faridabad', 'Gurgaon', 'Panipat', 'Ambala', 'Yamunanagar', 'Rohtak', 'Hisar', 'Karnal', 'Sonipat'],
  'Jharkhand': ['Ranchi', 'Jamshedpur', 'Dhanbad', 'Bokaro', 'Hazaribagh', 'Deoghar', 'Giridih'],
  'Chhattisgarh': ['Raipur', 'Bhilai', 'Bilaspur', 'Korba', 'Durg', 'Rajnandgaon', 'Jagdalpur'],
  'Assam': ['Guwahati', 'Silchar', 'Dibrugarh', 'Jorhat', 'Nagaon', 'Tinsukia', 'Tezpur'],
  'Uttarakhand': ['Dehradun', 'Haridwar', 'Roorkee', 'Haldwani', 'Rudrapur', 'Kashipur', 'Rishikesh'],
  'Himachal Pradesh': ['Shimla', 'Manali', 'Dharamshala', 'Solan', 'Mandi', 'Kullu', 'Hamirpur'],
  'Goa': ['Panaji', 'Margao', 'Vasco da Gama', 'Mapusa', 'Ponda'],
  'Chandigarh': ['Chandigarh'],
  'Jammu and Kashmir': ['Srinagar', 'Jammu', 'Anantnag', 'Baramulla', 'Sopore', 'Kathua'],
  'Ladakh': ['Leh', 'Kargil'],
  'Tripura': ['Agartala', 'Udaipur', 'Dharmanagar'],
  'Meghalaya': ['Shillong', 'Tura', 'Jowai'],
  'Manipur': ['Imphal', 'Thoubal', 'Bishnupur'],
  'Nagaland': ['Dimapur', 'Kohima', 'Mokokchung'],
  'Mizoram': ['Aizawl', 'Lunglei', 'Champhai'],
  'Arunachal Pradesh': ['Itanagar', 'Naharlagun', 'Pasighat'],
  'Sikkim': ['Gangtok', 'Namchi', 'Singtam'],
};

// Common pincodes for major cities (expandable)
const CITY_PINCODES: Record<string, string[]> = {
  'Mumbai': ['400001', '400002', '400003', '400004', '400005', '400006', '400007', '400008', '400010', '400011', '400012', '400013', '400014', '400015', '400016', '400017', '400018', '400019', '400020'],
  'Pune': ['411001', '411002', '411003', '411004', '411005', '411006', '411007', '411008', '411009', '411011', '411012', '411013', '411014', '411015', '411016', '411017', '411018', '411019', '411020', '411021', '411027', '411028', '411030', '411033', '411036', '411037', '411038', '411039', '411040', '411041', '411042', '411043', '411044', '411045', '411046', '411047', '411048', '411051', '411052', '411057', '411058'],
  'Bangalore': ['560001', '560002', '560003', '560004', '560005', '560006', '560007', '560008', '560009', '560010', '560011', '560012', '560013', '560014', '560015', '560016', '560017', '560018', '560019', '560020'],
  'Delhi': ['110001', '110002', '110003', '110004', '110005', '110006', '110007', '110008', '110009', '110010', '110011', '110012', '110013', '110014', '110015', '110016', '110017', '110018', '110019', '110020'],
  'New Delhi': ['110001', '110002', '110003', '110004', '110005', '110006', '110011', '110021', '110023', '110024', '110025', '110029', '110049', '110060', '110062', '110065', '110066', '110067', '110068', '110069', '110070'],
  'Chennai': ['600001', '600002', '600003', '600004', '600005', '600006', '600007', '600008', '600009', '600010', '600011', '600012', '600013', '600014', '600015', '600016', '600017', '600018', '600019', '600020'],
  'Hyderabad': ['500001', '500002', '500003', '500004', '500005', '500006', '500007', '500008', '500009', '500010', '500011', '500012', '500013', '500014', '500015', '500016', '500017', '500018', '500019', '500020'],
  'Kolkata': ['700001', '700002', '700003', '700004', '700005', '700006', '700007', '700008', '700009', '700010', '700011', '700012', '700013', '700014', '700015', '700016', '700017', '700018', '700019', '700020'],
  'Ahmedabad': ['380001', '380002', '380003', '380004', '380005', '380006', '380007', '380008', '380009', '380010', '380013', '380014', '380015', '380016', '380018', '380019', '380021', '380022', '380023', '380024'],
  'Surat': ['395001', '395002', '395003', '395004', '395005', '395006', '395007', '395008', '395009', '395010'],
  'Jaipur': ['302001', '302002', '302003', '302004', '302005', '302006', '302007', '302008', '302010', '302012', '302013', '302015', '302016', '302017', '302018', '302019', '302020', '302021', '302022'],
  'Lucknow': ['226001', '226002', '226003', '226004', '226005', '226006', '226007', '226008', '226009', '226010', '226011', '226012', '226013', '226014', '226015', '226016', '226017', '226018', '226019', '226020'],
};

interface LocationSelectorProps {
  state: string;
  city: string;
  pincode: string;
  onStateChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onPincodeChange: (value: string) => void;
  disabled?: boolean;
}

export default function LocationSelector({
  state,
  city,
  pincode,
  onStateChange,
  onCityChange,
  onPincodeChange,
  disabled = false
}: LocationSelectorProps) {
  const [stateSearch, setStateSearch] = useState('');
  const [citySearch, setCitySearch] = useState('');
  const [pincodeSearch, setPincodeSearch] = useState('');
  const [stateOpen, setStateOpen] = useState(false);
  const [cityOpen, setCityOpen] = useState(false);
  const [pincodeOpen, setPincodeOpen] = useState(false);

  const stateRef = useRef<HTMLDivElement>(null);
  const cityRef = useRef<HTMLDivElement>(null);
  const pincodeRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (stateRef.current && !stateRef.current.contains(e.target as Node)) setStateOpen(false);
      if (cityRef.current && !cityRef.current.contains(e.target as Node)) setCityOpen(false);
      if (pincodeRef.current && !pincodeRef.current.contains(e.target as Node)) setPincodeOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Get filtered states
  const filteredStates = Object.keys(INDIA_DATA).filter(s =>
    s.toLowerCase().includes(stateSearch.toLowerCase())
  ).sort();

  // Get cities for selected state
  const availableCities = state ? (INDIA_DATA[state] || []) : [];
  const filteredCities = availableCities.filter(c =>
    c.toLowerCase().includes(citySearch.toLowerCase())
  ).sort();

  // Get pincodes for selected city
  const availablePincodes = city ? (CITY_PINCODES[city] || []) : [];
  const filteredPincodes = availablePincodes.filter(p =>
    p.includes(pincodeSearch)
  ).sort();

  // Handle state selection
  const handleStateSelect = (selectedState: string) => {
    onStateChange(selectedState);
    onCityChange(''); // Reset city
    onPincodeChange(''); // Reset pincode
    setStateSearch('');
    setStateOpen(false);
  };

  // Handle city selection
  const handleCitySelect = (selectedCity: string) => {
    onCityChange(selectedCity);
    onPincodeChange(''); // Reset pincode
    setCitySearch('');
    setCityOpen(false);
  };

  // Handle pincode selection
  const handlePincodeSelect = (selectedPincode: string) => {
    onPincodeChange(selectedPincode);
    setPincodeSearch('');
    setPincodeOpen(false);
  };

  return (
    <div className="space-y-4">
      {/* State Dropdown */}
      <div ref={stateRef} className="relative">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          State *
        </label>
        <button
          type="button"
          onClick={() => !disabled && setStateOpen(!stateOpen)}
          disabled={disabled}
          className={`w-full px-4 py-3 border rounded-lg text-left flex items-center justify-between ${
            disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white cursor-pointer hover:border-gray-400'
          } ${stateOpen ? 'border-blue-500 ring-2 ring-blue-100' : 'border-gray-300'}`}
          data-testid="select-state-dropdown"
        >
          <span className={state ? 'text-gray-900' : 'text-gray-400'}>
            {state || 'Select State'}
          </span>
          <ChevronDown className={`h-5 w-5 text-gray-400 transition-transform ${stateOpen ? 'rotate-180' : ''}`} />
        </button>
        
        {stateOpen && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-hidden">
            {/* Search */}
            <div className="p-2 border-b border-gray-100">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  value={stateSearch}
                  onChange={(e) => setStateSearch(e.target.value)}
                  placeholder="Search state..."
                  className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded focus:outline-none focus:border-blue-500"
                  autoFocus
                />
              </div>
            </div>
            {/* Options */}
            <div className="max-h-48 overflow-y-auto">
              {filteredStates.length === 0 ? (
                <p className="px-4 py-3 text-sm text-gray-500">No states found</p>
              ) : (
                filteredStates.map(s => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => handleStateSelect(s)}
                    className={`w-full px-4 py-2.5 text-left text-sm hover:bg-blue-50 flex items-center gap-2 ${
                      s === state ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                    }`}
                  >
                    <MapPin className="h-4 w-4 text-gray-400" />
                    {s}
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* City Dropdown */}
      <div ref={cityRef} className="relative">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          City *
        </label>
        <button
          type="button"
          onClick={() => !disabled && state && setCityOpen(!cityOpen)}
          disabled={disabled || !state}
          className={`w-full px-4 py-3 border rounded-lg text-left flex items-center justify-between ${
            disabled || !state ? 'bg-gray-100 cursor-not-allowed' : 'bg-white cursor-pointer hover:border-gray-400'
          } ${cityOpen ? 'border-blue-500 ring-2 ring-blue-100' : 'border-gray-300'}`}
          data-testid="select-city-dropdown"
        >
          <span className={city ? 'text-gray-900' : 'text-gray-400'}>
            {city || (state ? 'Select City' : 'Select State First')}
          </span>
          <ChevronDown className={`h-5 w-5 text-gray-400 transition-transform ${cityOpen ? 'rotate-180' : ''}`} />
        </button>
        
        {cityOpen && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-hidden">
            <div className="p-2 border-b border-gray-100">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  value={citySearch}
                  onChange={(e) => setCitySearch(e.target.value)}
                  placeholder="Search city..."
                  className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded focus:outline-none focus:border-blue-500"
                  autoFocus
                />
              </div>
            </div>
            <div className="max-h-48 overflow-y-auto">
              {filteredCities.length === 0 ? (
                <p className="px-4 py-3 text-sm text-gray-500">No cities found</p>
              ) : (
                filteredCities.map(c => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => handleCitySelect(c)}
                    className={`w-full px-4 py-2.5 text-left text-sm hover:bg-blue-50 flex items-center gap-2 ${
                      c === city ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                    }`}
                  >
                    <MapPin className="h-4 w-4 text-gray-400" />
                    {c}
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Pincode Dropdown */}
      <div ref={pincodeRef} className="relative">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          PIN Code *
        </label>
        <button
          type="button"
          onClick={() => !disabled && city && setPincodeOpen(!pincodeOpen)}
          disabled={disabled || !city}
          className={`w-full px-4 py-3 border rounded-lg text-left flex items-center justify-between ${
            disabled || !city ? 'bg-gray-100 cursor-not-allowed' : 'bg-white cursor-pointer hover:border-gray-400'
          } ${pincodeOpen ? 'border-blue-500 ring-2 ring-blue-100' : 'border-gray-300'}`}
          data-testid="select-pincode-dropdown"
        >
          <span className={pincode ? 'text-gray-900' : 'text-gray-400'}>
            {pincode || (city ? 'Select PIN Code' : 'Select City First')}
          </span>
          <ChevronDown className={`h-5 w-5 text-gray-400 transition-transform ${pincodeOpen ? 'rotate-180' : ''}`} />
        </button>
        
        {pincodeOpen && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-hidden">
            <div className="p-2 border-b border-gray-100">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  value={pincodeSearch}
                  onChange={(e) => setPincodeSearch(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
                  placeholder="Search or enter PIN code..."
                  className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded focus:outline-none focus:border-blue-500"
                  autoFocus
                />
              </div>
            </div>
            <div className="max-h-48 overflow-y-auto">
              {/* Allow manual entry if not in list */}
              {pincodeSearch.length === 6 && !availablePincodes.includes(pincodeSearch) && (
                <button
                  type="button"
                  onClick={() => handlePincodeSelect(pincodeSearch)}
                  className="w-full px-4 py-2.5 text-left text-sm bg-blue-50 text-blue-700 hover:bg-blue-100 flex items-center gap-2"
                >
                  <MapPin className="h-4 w-4" />
                  Use "{pincodeSearch}"
                </button>
              )}
              {filteredPincodes.length === 0 && pincodeSearch.length < 6 ? (
                <p className="px-4 py-3 text-sm text-gray-500">
                  {availablePincodes.length === 0 
                    ? 'Enter 6-digit PIN code manually'
                    : 'No PIN codes found'}
                </p>
              ) : (
                filteredPincodes.map(p => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => handlePincodeSelect(p)}
                    className={`w-full px-4 py-2.5 text-left text-sm hover:bg-blue-50 flex items-center gap-2 ${
                      p === pincode ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                    }`}
                  >
                    <MapPin className="h-4 w-4 text-gray-400" />
                    {p}
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
