from app.shopify_tool import _gql

data = _gql("""
query {
  appInstallation {
    accessScopes { handle }
  }
}
""")
print(data)