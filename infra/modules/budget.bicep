// The demo's own budget: an email when this resource group's spending passes half, and all, of a small amount.
// A budget only alerts; it never stops spending. The subscription's spending limit is the hard stop.

@description('The budget\'s name.')
param name string

@description('The monthly amount, in the billing currency.')
param amount int

@description('The first day of the first month the budget covers, as yyyy-MM-dd.')
param startDate string

@description('Who gets the alerts.')
param alertEmail string

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: name
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
    }
    notifications: {
      half: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 50
        thresholdType: 'Actual'
        contactEmails: [alertEmail]
      }
      all: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: [alertEmail]
      }
    }
  }
}
