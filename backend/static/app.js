function app() {
    return {
        // State
        analysis: null,
        costResult: null,
        metal: 'Aluminum_A380',
        annualVolume: '',
        fileName: '',
        stlUrl: null,
        marketData: null,
        priceHistory: [],
        hostIp: null,
        kernels: [],
        location: { name: 'India (Pune Node)', multiplier: 0.78, market_status: 'BULLISH' },
        locationQuery: '',
        locationResults: [],
        isProcessing: false,
        isUpdatingChart: false,
        
        // Libraries
        three: null,
        priceChart: null,
        breakdownChart: null,

        initApp() {
            this.initThree();
            this.fetchHostStatus();
            this.fetchMarketData();
            
            // Poll for UI updates every minute
            setInterval(() => this.fetchMarketData(), 60000); 
            
            // GSAP Entrance
            gsap.to('.gsap-header', { opacity: 1, y: 0, duration: 1, ease: 'power4.out' });
            gsap.to('.gsap-card', { opacity: 1, y: 0, duration: 1, delay: 0.2, stagger: 0.1, ease: 'power4.out' });
        },

        initThree() {
            const container = document.getElementById('canvas-container');
            if (!container) return;
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            const ambient = new THREE.AmbientLight(0xffffff, 0.4);
            scene.add(ambient);
            const directional = new THREE.DirectionalLight(0x00f3ff, 0.8);
            directional.position.set(100, 100, 100);
            scene.add(directional);

            camera.position.set(120, 120, 120);
            camera.lookAt(0, 0, 0);

            this.three = { scene, camera, renderer, loader: new THREE.STLLoader() };

            const animate = () => {
                requestAnimationFrame(animate);
                if (this.three.mesh) {
                    this.three.mesh.rotation.y += 0.005;
                }
                renderer.render(scene, camera);
            };
            animate();

            window.addEventListener('resize', () => {
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            });
        },

        loadMeshFromBase64(base64Str) {
            const raw = base64Str.replace(/^data:model\/stl;base64,/, '');
            const binary = atob(raw);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            
            const geometry = this.three.loader.parse(bytes.buffer);
            if (this.three.mesh) this.three.scene.remove(this.three.mesh);
            
            geometry.center();
            geometry.computeVertexNormals();
            const material = new THREE.MeshStandardMaterial({ 
                color: 0x00f3ff, metalness: 0.8, roughness: 0.2 
            });
            const mesh = new THREE.Mesh(geometry, material);
            
            const box = new THREE.Box3().setFromObject(mesh);
            const size = box.getSize(new THREE.Vector3()).length();
            const scale = 110 / size;
            mesh.scale.set(scale, scale, scale);
            
            this.three.scene.add(mesh);
            this.three.mesh = mesh;
            this.stlUrl = 'loaded';
        },

        async searchLocation() {
            if (this.locationQuery.length < 2) {
                this.locationResults = [];
                return;
            }
            try {
                const res = await fetch(`/api/search-location?q=${encodeURIComponent(this.locationQuery)}`);
                this.locationResults = await res.json();
            } catch (err) {
                console.error("Location search failed:", err);
            }
        },

        selectLocation(loc) {
            this.location = loc;
            this.locationQuery = loc.name;
            this.locationResults = [];
            if (this.analysis) this.calculateCost();
        },

        async agentProcess(e) {
            const file = e.target.files[0];
            if (!file) return;
            this.fileName = file.name;
            this.isProcessing = true;
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('metal', this.metal);
            if (this.annualVolume) formData.append('annual_volume', this.annualVolume);
            formData.append('location_name', this.location.name);
            formData.append('location_multiplier', this.location.multiplier);
            
            try {
                const res = await fetch('/api/agent/process', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                
                const report = data.agent_report;
                this.analysis = {
                    traits: report.technical_matrix,
                    engine: report.engine,
                    analysis_id: report.analysis_id
                };
                this.costResult = report.cost_estimation;
                
                if (report.technical_matrix.preview_mesh) {
                    this.loadMeshFromBase64(report.technical_matrix.preview_mesh);
                }
                
                // Ensure DOM is ready for breakdownChart
                setTimeout(() => this.updateCharts(), 100);
            } catch (err) {
                alert("Agent Failure: " + err.message);
            } finally {
                this.isProcessing = false;
            }
        },

        async calculateCost() {
            if (!this.analysis) return;
            try {
                const res = await fetch('/api/estimate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        analysis_id: this.analysis.analysis_id,
                        metal: this.metal,
                        annual_volume: this.annualVolume ? parseInt(this.annualVolume) : null,
                        location_name: this.location.name,
                        location_multiplier: this.location.multiplier
                    })
                });
                const data = await res.json();
                this.costResult = data.cost_breakdown;
                setTimeout(() => this.updateCharts(), 100);
            } catch (err) {
                console.error(err);
            }
        },

        async fetchMarketData() {
            try {
                const res = await fetch('/api/market-data');
                this.marketData = await res.json();
                
                const currentPrice = this.marketData.current_base_rates[this.metal]?.current_price || 0;
                this.priceHistory.push({ time: new Date().toLocaleTimeString(), price: currentPrice });
                if (this.priceHistory.length > 20) this.priceHistory.shift();
                
                this.updatePriceChart();
            } catch (err) {
                console.error(err);
            }
        },

        async fetchHostStatus() {
            try {
                const res = await fetch('/api/health');
                const data = await res.json();
                this.hostIp = data.host_ip;
                this.kernels = data.kernels;
            } catch (err) {
                console.error("Host status fail:", err);
            }
        },

        updatePriceChart() {
            if (this.isUpdatingChart) return;
            const chartCanvas = document.getElementById('priceChart');
            if (!chartCanvas) return;
            const ctx = chartCanvas.getContext('2d');
            
            this.isUpdatingChart = true;
            if (this.priceChart) {
                this.priceChart.destroy();
                this.priceChart = null; 
            }

            try {
                this.priceChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: this.priceHistory.map(h => h.time),
                        datasets: [{
                            label: 'Market_Spot',
                            data: this.priceHistory.map(h => h.price),
                            borderColor: '#00f3ff',
                            borderWidth: 2,
                            pointRadius: 0,
                            fill: true,
                            backgroundColor: 'rgba(0, 243, 255, 0.05)',
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { display: false },
                            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 8 } } }
                        }
                    }
                });
            } catch (e) {
                console.warn("Price Chart Init Error:", e);
            } finally {
                this.isUpdatingChart = false;
            }
        },

        updateCharts() {
            const breakdownCanvas = document.getElementById('breakdownChart');
            if (!breakdownCanvas || !this.costResult) return;
            const ctx = breakdownCanvas.getContext('2d');
            
            const data = [
                this.costResult.material_cost || 0, 
                this.costResult.machine_cost || 0, 
                this.costResult.amortization || 0
            ];
            
            if (this.breakdownChart) {
                this.breakdownChart.destroy();
                this.breakdownChart = null;
            }
            
            try {
                this.breakdownChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Material', 'Process', 'Tools'],
                        datasets: [{
                            data: data,
                            backgroundColor: ['#00f3ff', '#7000ff', '#ff0070'],
                            borderWidth: 0,
                            hoverOffset: 10
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: false,
                        plugins: { legend: { position: 'bottom', labels: { color: '#888', font: { size: 10 }, padding: 20 } } },
                        cutout: '70%',
                        layout: { padding: 5 }
                    }
                });
            } catch (e) {
                console.warn("Breakdown Chart Init Error:", e);
            }
        },

        resetHistory() {
            this.priceHistory = [];
            this.updatePriceChart();
            if (this.analysis) this.calculateCost();
        }
    }
}
