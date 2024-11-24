import { User, UserRole, UserPreferences } from '../models/User';

type UserId = string;

interface IUserService {
  getUser(id: UserId): Promise<User>;
  updateUser(id: UserId, data: Partial<User>): Promise<User>;
  deleteUser(id: UserId): Promise<void>;
}

export class UserService implements IUserService {
  private users: Map<UserId, User> = new Map();

  public async getUser(id: UserId): Promise<User> {
    const user = this.users.get(id);
    if (!user) throw new Error(`User ${id} not found`);
    return user;
  }

  public async updateUser(id: UserId, data: Partial<User>): Promise<User> {
    const user = await this.getUser(id);
    Object.assign(user, data);
    return user;
  }

  public async deleteUser(id: UserId): Promise<void> {
    if (!this.users.delete(id)) {
      throw new Error(`User ${id} not found`);
    }
  }

  @Deprecated('Use createUser instead')
  public async addUser(data: Partial<User>): Promise<User> {
    return this.createUser(data);
  }

  public async createUser(data: Partial<User>): Promise<User> {
    const id = crypto.randomUUID();
    const user = new User(
      id,
      data.email ?? 'default@example.com'
    );
    this.users.set(id, user);
    return user;
  }
}
