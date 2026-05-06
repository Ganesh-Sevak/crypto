#include <cmath>
#include <iostream>
#include <numeric>
#include <vector>

double volatility(const std::vector<double>& prices) {
    if (prices.size() < 3) {
        return 0.0;
    }

    std::vector<double> returns;
    returns.reserve(prices.size() - 1);
    for (std::size_t i = 1; i < prices.size(); ++i) {
        returns.push_back((prices[i] - prices[i - 1]) / prices[i - 1]);
    }

    const double mean = std::accumulate(returns.begin(), returns.end(), 0.0) / returns.size();
    double variance = 0.0;
    for (double value : returns) {
        variance += (value - mean) * (value - mean);
    }
    return std::sqrt(variance / returns.size());
}

extern "C" double compute_volatility(const double* prices, int length) {
    if (prices == nullptr || length <= 0) {
        return 0.0;
    }
    return volatility(std::vector<double>(prices, prices + length));
}

int main() {
    const std::vector<double> prices = {100.0, 101.2, 100.4, 103.1, 102.7};
    std::cout << "Example volatility: " << volatility(prices) << std::endl;
    return 0;
}
