document.addEventListener('DOMContentLoaded', function () {
    // Grab chart element
    const chartElement = document.getElementById('ordersChart');
    if (!chartElement) return;

    // Parse data from data attributes (sent from Flask)
    const labels = JSON.parse(chartElement.dataset.labels || '[]');
    const data = JSON.parse(chartElement.dataset.data || '[]');

    // Initialize Chart.js bar chart
    new Chart(chartElement.getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Orders',
                data: data,
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Monthly Orders Overview',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                },
                x: {
                    ticks: {
                        autoSkip: false
                    }
                }
            }
        }
    });
});
