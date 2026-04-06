import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Home from './pages/Home'
import Search from './pages/Search'
import Alerts from './pages/Alerts'
import Network from './pages/Network'
import MapView from './pages/MapView'
import ContractorDetail from './pages/ContractorDetail'
import TenderDetail from './pages/TenderDetail'
import BuyerDetail from './pages/BuyerDetail'
import About from './pages/About'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="search" element={<Search />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="network" element={<Network />} />
          <Route path="network/:contractorId" element={<Network />} />
          <Route path="map" element={<MapView />} />
          <Route path="contractor/:contractorId" element={<ContractorDetail />} />
          <Route path="tender/:tenderId" element={<TenderDetail />} />
          <Route path="buyer/:buyerId" element={<BuyerDetail />} />
          <Route path="about" element={<About />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
